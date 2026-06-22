#!/usr/bin/env python3
"""
Parallel translation script - uses async/concurrent API calls for speed.
Translates modules individually in parallel.
"""

import json
import sys
import os
import time
import re
import asyncio
import httpx

script_dir = os.path.dirname(os.path.abspath(__file__))

def load_config():
    config_path = os.path.join(script_dir, 'transpage_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_json_response(content):
    """Clean API response to valid JSON."""
    content = content.strip()
    if content.startswith('```'):
        lines = content.split('\n')
        lines = [l for l in lines if not l.strip().startswith('```')]
        content = '\n'.join(lines)
    # Remove control characters except \n \r \t
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
    return content

async def translate_chunk_async(client, config, chunk_data, target_lang, lang_name, chunk_name="", max_retries=5):
    """Translate a JSON chunk asynchronously."""
    api_url = f"{config['api_base_url'].rstrip('/')}/chat/completions"

    protected = config.get('protected_terms', {}).get('technical_terms', [])
    game_names = config.get('protected_terms', {}).get('game_names', [])
    all_protected = protected + game_names

    chunk_json = json.dumps(chunk_data, indent=2, ensure_ascii=False)

    prompt = f"""Translate the following JSON from English to {lang_name}.
Rules:
1. Keep ALL JSON keys exactly the same
2. Only translate string values
3. Keep untranslated: {', '.join(all_protected[:20])}
4. Keep URLs, HTML tags, placeholders ({{count}}) unchanged
5. Return ONLY valid JSON, no markdown
6. Keep exact same structure

{chunk_json}"""

    for attempt in range(max_retries):
        try:
            response = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config['model'],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": config.get('temperature', 0.1),
                    "max_tokens": config.get('max_tokens', 32768)
                }
            )

            if response.status_code != 200:
                print(f"      [{chunk_name}] API error {response.status_code} (attempt {attempt+1})", flush=True)
                await asyncio.sleep(10)
                continue

            result = response.json()
            content = result['choices'][0]['message']['content']
            content = clean_json_response(content)
            translated = json.loads(content)
            return translated

        except json.JSONDecodeError as e:
            print(f"      [{chunk_name}] JSON error (attempt {attempt+1}): {str(e)[:80]}", flush=True)
            await asyncio.sleep(5)
        except httpx.TimeoutException:
            print(f"      [{chunk_name}] Timeout (attempt {attempt+1})", flush=True)
            await asyncio.sleep(10)
        except Exception as e:
            print(f"      [{chunk_name}] Error (attempt {attempt+1}): {str(e)[:80]}", flush=True)
            await asyncio.sleep(5)

    return None

async def translate_language_async(config, en_data, target_lang, exclude_sections=None):
    """Translate entire en.json to target language with parallel API calls."""
    exclude_sections = exclude_sections or []
    lang_name = config.get('lang_names', {}).get(target_lang, target_lang)

    project_root = os.path.normpath(os.path.join(script_dir, '..', '..', '..', '..'))
    output_path = os.path.join(project_root, 'src', 'locales', f'{target_lang}.json')

    # Load existing translation
    existing = {}
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)

    result = {}

    async with httpx.AsyncClient(timeout=180.0) as client:
        # Phase 1: Translate non-modules sections (in parallel, 3 at a time)
        small_sections = {}
        for key, data in en_data.items():
            if key in exclude_sections:
                if key in existing:
                    result[key] = existing[key]
                    print(f"  [{key}] Kept existing (excluded)", flush=True)
                else:
                    result[key] = data
                    print(f"  [{key}] Keeping English (excluded)", flush=True)
            elif key == 'modules':
                pass  # Handle separately
            else:
                small_sections[key] = data

        # Translate small sections in parallel (max 3 concurrent)
        semaphore = asyncio.Semaphore(2)

        async def translate_with_limit(key, data):
            async with semaphore:
                chunk = {key: data}
                translated = await translate_chunk_async(client, config, chunk, target_lang, lang_name, chunk_name=key)
                return key, translated

        print(f"  Translating {len(small_sections)} sections in parallel...", flush=True)
        tasks = [translate_with_limit(k, v) for k, v in small_sections.items()]
        results = await asyncio.gather(*tasks)

        for key, translated in results:
            if translated and key in translated:
                result[key] = translated[key]
                print(f"  [{key}] OK", flush=True)
            else:
                result[key] = en_data[key]
                print(f"  [{key}] FAILED", flush=True)

        # Phase 2: Translate modules in parallel (max 3 concurrent)
        if 'modules' in en_data and 'modules' not in exclude_sections:
            modules_data = en_data['modules']
            print(f"  Translating {len(modules_data)} modules in parallel (3 concurrent)...", flush=True)

            async def translate_module(mod_key, mod_data):
                async with semaphore:
                    chunk = {mod_key: mod_data}
                    translated = await translate_chunk_async(
                        client, config, chunk, target_lang, lang_name,
                        chunk_name=mod_key
                    )
                    return mod_key, translated

            mod_tasks = [translate_module(k, v) for k, v in modules_data.items()]
            mod_results = await asyncio.gather(*mod_tasks)

            modules_result = {}
            ok_count = 0
            fail_count = 0
            for mod_key, translated in mod_results:
                if translated and mod_key in translated:
                    modules_result[mod_key] = translated[mod_key]
                    ok_count += 1
                else:
                    modules_result[mod_key] = modules_data[mod_key]
                    fail_count += 1

            result['modules'] = modules_result
            print(f"  [modules] {ok_count} OK, {fail_count} failed", flush=True)

    # Ensure correct key order (match en.json)
    ordered_result = {}
    for key in en_data:
        if key in result:
            ordered_result[key] = result[key]

    # Write result
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ordered_result, f, indent=2, ensure_ascii=False)
        f.write('\n')

    size = os.path.getsize(output_path)
    print(f"  Saved: {output_path} ({size} bytes)", flush=True)
    return True

async def main_async():
    config = load_config()

    exclude_sections = ['pages', 'nav']
    langs = config.get('languages', [])

    if '--lang' in sys.argv:
        idx = sys.argv.index('--lang')
        if idx + 1 < len(sys.argv):
            langs = sys.argv[idx + 1].split(',')

    if '--exclude-sections' in sys.argv:
        idx = sys.argv.index('--exclude-sections')
        if idx + 1 < len(sys.argv):
            exclude_sections = sys.argv[idx + 1].split(',')

    project_root = os.path.normpath(os.path.join(script_dir, '..', '..', '..', '..'))
    en_path = os.path.join(project_root, 'src', 'locales', 'en.json')

    print(f"Source: {en_path}", flush=True)
    print(f"Languages: {langs}", flush=True)
    print(f"Exclude: {exclude_sections}", flush=True)
    print(f"Model: {config['model']}", flush=True)

    with open(en_path, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    success = 0
    failed = 0

    for lang in langs:
        print(f"\n{'='*60}", flush=True)
        print(f"Translating to {lang.upper()}", flush=True)
        print(f"{'='*60}", flush=True)

        start = time.time()
        try:
            if await translate_language_async(config, en_data, lang, exclude_sections):
                elapsed = time.time() - start
                print(f"  Completed in {elapsed:.0f}s", flush=True)
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}", flush=True)
    print(f"Done: {success} success, {failed} failed out of {len(langs)}", flush=True)
    print(f"{'='*60}", flush=True)

if __name__ == '__main__':
    asyncio.run(main_async())
