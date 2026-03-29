#!/usr/bin/env python3
"""
Fast translation using requests + ThreadPoolExecutor for parallel API calls.
"""

import json
import sys
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.normpath(os.path.join(script_dir, '..', '..', '..', '..'))

def load_config():
    with open(os.path.join(script_dir, 'transpage_config.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

def translate_chunk(config, chunk_data, target_lang, lang_name, chunk_name="", max_retries=5):
    api_url = f"{config['api_base_url'].rstrip('/')}/chat/completions"
    protected = config.get('protected_terms', {}).get('technical_terms', [])
    game_names = config.get('protected_terms', {}).get('game_names', [])
    all_protected = list(set(protected + game_names))

    chunk_json = json.dumps(chunk_data, indent=2, ensure_ascii=False)

    prompt = f"""Translate JSON from English to {lang_name}. Keep keys unchanged. Only translate values. Keep {', '.join(all_protected[:15])} untranslated. Keep URLs/HTML/placeholders. Return ONLY valid JSON.

{chunk_json}"""

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                api_url,
                headers={'Authorization': f'Bearer {config["api_key"]}', 'Content-Type': 'application/json'},
                json={
                    'model': config['model'],
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.1,
                    'max_tokens': config.get('max_tokens', 32768)
                },
                timeout=180
            )

            if resp.status_code != 200:
                print(f"    [{chunk_name}] API {resp.status_code} (try {attempt+1})", flush=True)
                time.sleep(10)
                continue

            content = resp.json()['choices'][0]['message']['content'].strip()
            # Clean markdown blocks
            if content.startswith('```'):
                lines = content.split('\n')
                lines = [l for l in lines if not l.strip().startswith('```')]
                content = '\n'.join(lines)
            # Clean control chars
            content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)

            return json.loads(content)

        except requests.exceptions.Timeout:
            print(f"    [{chunk_name}] Timeout (try {attempt+1})", flush=True)
            time.sleep(5)
        except json.JSONDecodeError as e:
            print(f"    [{chunk_name}] JSON error (try {attempt+1}): {str(e)[:60]}", flush=True)
            time.sleep(3)
        except Exception as e:
            print(f"    [{chunk_name}] Error (try {attempt+1}): {str(e)[:60]}", flush=True)
            time.sleep(5)

    return None

def translate_language(config, en_data, target_lang, exclude_sections):
    lang_name = config.get('lang_names', {}).get(target_lang, target_lang)
    output_path = os.path.join(project_root, 'src', 'locales', f'{target_lang}.json')

    existing = {}
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)

    result = {}

    # Separate tasks
    section_tasks = []  # (key, data)
    module_tasks = []   # (key, data)

    for key, data in en_data.items():
        if key in exclude_sections:
            if key in existing:
                result[key] = existing[key]
            else:
                result[key] = data
            print(f"  [{key}] excluded (kept)", flush=True)
        elif key == 'modules' and isinstance(data, dict):
            for mod_key, mod_data in data.items():
                module_tasks.append((mod_key, {mod_key: mod_data}))
        else:
            section_tasks.append((key, {key: data}))

    # Translate sections + modules in parallel with ThreadPoolExecutor
    all_tasks = section_tasks + module_tasks
    total = len(all_tasks)
    print(f"  {total} chunks to translate ({len(section_tasks)} sections + {len(module_tasks)} modules)", flush=True)

    translated_chunks = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for name, chunk_data in all_tasks:
            future = executor.submit(translate_chunk, config, chunk_data, target_lang, lang_name, chunk_name=name)
            futures[future] = name

        done_count = 0
        for future in as_completed(futures):
            name = futures[future]
            done_count += 1
            try:
                translated = future.result()
                if translated:
                    translated_chunks[name] = translated
                    print(f"  [{done_count}/{total}] {name} OK", flush=True)
                else:
                    print(f"  [{done_count}/{total}] {name} FAILED", flush=True)
            except Exception as e:
                print(f"  [{done_count}/{total}] {name} ERROR: {e}", flush=True)

    # Assemble result in correct order
    for key, data in en_data.items():
        if key in exclude_sections:
            continue  # Already handled
        elif key == 'modules':
            modules_result = {}
            for mod_key in data:
                if mod_key in translated_chunks and mod_key in translated_chunks[mod_key]:
                    modules_result[mod_key] = translated_chunks[mod_key][mod_key]
                else:
                    modules_result[mod_key] = data[mod_key]
            result[key] = modules_result
        else:
            if key in translated_chunks and key in translated_chunks[key]:
                result[key] = translated_chunks[key][key]
            else:
                result[key] = data

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write('\n')

    size = os.path.getsize(output_path)
    print(f"  Saved: {output_path} ({size} bytes)", flush=True)

def main():
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

    en_path = os.path.join(project_root, 'src', 'locales', 'en.json')
    with open(en_path, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    print(f"Languages: {langs}", flush=True)
    print(f"Exclude: {exclude_sections}", flush=True)
    print(f"Model: {config['model']}", flush=True)
    print(f"Sections: {list(en_data.keys())}", flush=True)
    print(f"Modules: {len(en_data.get('modules', {}))}", flush=True)

    for lang in langs:
        print(f"\n{'='*50}", flush=True)
        print(f"  {lang.upper()}", flush=True)
        print(f"{'='*50}", flush=True)
        start = time.time()
        translate_language(config, en_data, lang, exclude_sections)
        elapsed = time.time() - start
        print(f"  Done in {elapsed:.0f}s", flush=True)

    print("\nAll done!", flush=True)

if __name__ == '__main__':
    main()
