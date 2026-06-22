#!/usr/bin/env python3
"""
Chunked translation script - splits large sections (like modules) into individual items.
Translates en.json into target languages, section by section.
"""

import json
import sys
import os
import time
import httpx

script_dir = os.path.dirname(os.path.abspath(__file__))

def load_config():
    config_path = os.path.join(script_dir, 'transpage_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def translate_chunk(config, chunk_data, target_lang, lang_name, context=""):
    """Translate a JSON chunk to target language."""
    api_url = f"{config['api_base_url'].rstrip('/')}/chat/completions"

    protected = config.get('protected_terms', {}).get('technical_terms', [])
    game_names = config.get('protected_terms', {}).get('game_names', [])
    all_protected = protected + game_names

    chunk_json = json.dumps(chunk_data, indent=2, ensure_ascii=False)

    prompt = f"""Translate the following JSON content from English to {lang_name}.

Rules:
1. Keep ALL JSON keys exactly the same (do not translate keys)
2. Only translate the string values
3. Keep these terms untranslated: {', '.join(all_protected)}
4. Keep URLs, HTML tags, and placeholders (like {{count}}) unchanged
5. Return ONLY valid JSON, no markdown code blocks
6. Maintain the exact same JSON structure
{context}

JSON to translate:
{chunk_json}"""

    for attempt in range(config.get('retry_attempts', 5)):
        try:
            with httpx.Client(timeout=900.0) as client:
                response = client.post(
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
                    print(f"    API error {response.status_code}: {response.text[:200]}", flush=True)
                    time.sleep(config.get('retry_delay', 10))
                    continue

                result = response.json()
                content = result['choices'][0]['message']['content']

                # Clean markdown code blocks if present
                content = content.strip()
                if content.startswith('```'):
                    lines = content.split('\n')
                    # Remove first and last lines (```json and ```)
                    lines = [l for l in lines if not l.strip().startswith('```')]
                    content = '\n'.join(lines)

                try:
                    translated = json.loads(content)
                    return translated
                except json.JSONDecodeError:
                    # Try fixing control characters
                    import re
                    cleaned = re.sub(r'[\x00-\x1f\x7f](?<![\n\t\r])', '', content)
                    # Also fix common issues: unescaped newlines in strings
                    translated = json.loads(cleaned)
                    return translated

        except json.JSONDecodeError as e:
            print(f"    JSON parse error (attempt {attempt+1}): {e}", flush=True)
            time.sleep(5)
        except httpx.TimeoutException:
            print(f"    Timeout (attempt {attempt+1})", flush=True)
            time.sleep(10)
        except Exception as e:
            print(f"    Error (attempt {attempt+1}): {e}", flush=True)
            time.sleep(5)

    return None

def translate_language(config, en_data, target_lang, exclude_sections=None):
    """Translate entire en.json to target language, section by section."""
    exclude_sections = exclude_sections or []
    lang_name = config.get('lang_names', {}).get(target_lang, target_lang)

    output_path = os.path.join(
        os.path.dirname(script_dir),  # modules dir
        '..', '..', '..', '..', 'src', 'locales', f'{target_lang}.json'
    )
    output_path = os.path.normpath(output_path)

    # Load existing translation if available
    existing = {}
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)

    result = {}

    for section_key, section_data in en_data.items():
        if section_key in exclude_sections:
            # Keep existing translation for excluded sections
            if section_key in existing:
                result[section_key] = existing[section_key]
                print(f"  [{section_key}] Kept existing (excluded)", flush=True)
            else:
                result[section_key] = section_data
                print(f"  [{section_key}] No existing, keeping English (excluded)", flush=True)
            continue

        # For the large "modules" section, batch modules into ~15000 char chunks
        if section_key == 'modules' and isinstance(section_data, dict):
            print(f"  [{section_key}] Translating {len(section_data)} modules in batches...", flush=True)
            modules_result = {}

            # Group modules into batches of ~15000 chars
            MAX_BATCH_CHARS = 8000
            batches = []
            current_batch = {}
            current_size = 0

            for mod_key, mod_data in section_data.items():
                mod_size = len(json.dumps(mod_data, ensure_ascii=False))
                if current_size + mod_size > MAX_BATCH_CHARS and current_batch:
                    batches.append(current_batch)
                    current_batch = {}
                    current_size = 0
                current_batch[mod_key] = mod_data
                current_size += mod_size

            if current_batch:
                batches.append(current_batch)

            print(f"    Split into {len(batches)} batches", flush=True)

            for i, batch in enumerate(batches):
                batch_keys = list(batch.keys())
                print(f"    Batch {i+1}/{len(batches)} ({len(batch_keys)} modules: {', '.join(batch_keys[:3])}...)", flush=True, end='')
                translated = translate_chunk(
                    config, batch, target_lang, lang_name,
                    context=f"\nThis is a game wiki. Each key is a module section. Translate naturally for {lang_name} speakers."
                )
                if translated:
                    for mk in batch_keys:
                        if mk in translated:
                            modules_result[mk] = translated[mk]
                        else:
                            modules_result[mk] = batch[mk]
                    print(f" OK", flush=True)
                else:
                    for mk in batch_keys:
                        modules_result[mk] = batch[mk]
                    print(f" FAILED (keeping English)", flush=True)

                time.sleep(2)

            result[section_key] = modules_result
        else:
            # Translate entire section as one chunk
            print(f"  [{section_key}] Translating...", flush=True, end='')
            chunk = {section_key: section_data}
            translated = translate_chunk(config, chunk, target_lang, lang_name)
            if translated and section_key in translated:
                result[section_key] = translated[section_key]
                print(f" OK", flush=True)
            else:
                result[section_key] = section_data
                print(f" FAILED (keeping English)", flush=True)

            time.sleep(1)

    # Write result
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"  Saved to {output_path} ({os.path.getsize(output_path)} bytes)", flush=True)
    return True

def main():
    config = load_config()

    # Parse arguments
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

    # Find en.json
    project_root = os.path.normpath(os.path.join(script_dir, '..', '..', '..', '..'))
    en_path = os.path.join(project_root, 'src', 'locales', 'en.json')

    print(f"Source: {en_path}", flush=True)
    print(f"Languages: {langs}", flush=True)
    print(f"Exclude: {exclude_sections}", flush=True)
    print(f"API: {config['api_base_url']}", flush=True)
    print(f"Model: {config['model']}", flush=True)

    with open(en_path, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    success = 0
    failed = 0

    for lang in langs:
        print(f"\n{'='*60}", flush=True)
        print(f"Translating to {lang.upper()}", flush=True)
        print(f"{'='*60}", flush=True)

        try:
            if translate_language(config, en_data, lang, exclude_sections):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            failed += 1

    print(f"\n{'='*60}", flush=True)
    print(f"Done: {success} success, {failed} failed", flush=True)
    print(f"{'='*60}", flush=True)

if __name__ == '__main__':
    main()
