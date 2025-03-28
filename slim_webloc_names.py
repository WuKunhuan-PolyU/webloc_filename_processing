import os, json, requests, toml, plistlib, time, sys, argparse, math, time
from typing import List, Dict

def find_webloc_files(directory: str = ".") -> List[str]:
    """Recursively find all .webloc files in the given directory."""
    webloc_files = []
    for root, _, files in os.walk(directory):
        for file in files: 
            full_path = os.path.join(root, file)
            if (parse_webloc(full_path)): 
                webloc_files.append(full_path)
    return webloc_files

def parse_webloc(filepath):
    """
    Check if a file is a webloc file and return its URL if it is.
    Returns None if not a webloc file or if there's an error.
    """
    try: 
        with open(filepath, 'rb') as f:
            plist = plistlib.load(f)
            return plist.get('URL', None)
    except Exception as e: 
        return None
    
def simplify_filenames(filepaths: List[str], api_key: str, batch_size: int = 5) -> Dict[str, str]:
    """
    Use OpenRouter API to simplify filenames in batches.
    
    Args:
        filenames: List of filepaths to simplify
        api_key: OpenRouter API key
        batch_size: Number of filenames to process in each API call
        
    Returns:
        Dictionary mapping original filepath to simplified filename (without extension)
    """
    simplified_names = {}
    batched_filepaths = []
    for i in range (math.ceil(len(filepaths) / batch_size)):
        batched_filepaths.append({'id': i, 'filenames': filepaths[i * batch_size: (i + 1) * batch_size], 'attempts': 0})
    
    # Process in batches
    failed_instances = []
    while (len(batched_filepaths) > 0): 
        start_time = time.time()
        try:
            batch_dict = batched_filepaths.pop(0)
            i = batch_dict['id']
            batch = batch_dict['filenames']
            print (f"BATCH {i + 1}/{math.ceil(len(filepaths) / batch_size)} ...", end = "")
            time.sleep(1)
            file_prefix_list = []

            # simulate errors
            # import random
            # if (random.random() < 0.3): 
            #     raise Exception("Simulated error")
            
            # Create prompt for the API
            prompt = (
                "Please simplify the following filenames by removing redundant or unrelated information while preserving the main content. \n\n"
                "1st example, '1泊2日で行ける！超弾丸香港ひとり旅！ガチで楽しすぎたww' should be simplified to '1泊2日で行ける！超弾丸香港ひとり旅！'. "
                "2nd example: '香港中文大学文物馆藏陶瓷精选展 康熙青花重器「万寿尊」领衔 | 近期展览 | THE VALUE | 艺术新闻' should be simplified to '香港中文大学文物馆藏陶瓷精选展，「万寿尊」领衔'.\n"
                "3rd example: '【全站首发】【深圳地铁】究极跳号？大鹏通铁路？深惠城际大鹏支线及深圳地铁32号线葵涌站探访实录' should be simplified to '深惠城际大鹏支线及深圳地铁32号线葵涌站探访实录'.\n"
                "You may choose to keep the original filename if it is already simple enough.\n\n"
                "Respond with a JSON list where values are the simplified versions in order with the original names. Value format: {'original': 'Original Name', 'simplified': 'Simplified Name'}\n\n"
                "Filenames to simplify: \n"
            )
            
            for filepath in batch: 
                basename = os.path.splitext(os.path.basename(filepath))[0]
                basename_split = basename.split(' - ')
                name_without_ext, prefix = basename_split[-1], basename_split[0] if len(basename_split) > 1 else ''
                file_prefix_list.append((filepath, prefix))
                prompt += f"- {name_without_ext}\n"
                
            # Call the API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/",
                "X-Title": "Filename Simplifier"
            }
            
            data = {
                "model": "deepseek/deepseek-chat-v3-0324:free",  # :free
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
        
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            response_content = response_data["choices"][0]["message"]["content"].replace('\n', '').replace('```', '').replace('json', '')
            simplified_batch = json.loads(response_content)
            
            # Update the main dictionary
            for i, simplified_name in enumerate(simplified_batch): 
                try: simplified_name = simplified_name['simplified']
                except: pass
                filepath = file_prefix_list[i][0]
                prefix = file_prefix_list[i][1]
                if prefix: simplified_name = f"{prefix} - {simplified_name}"
                simplified_names[filepath] = simplified_name
            
            # Sleep to avoid rate limiting
            end_time = time.time()
            print ("SUCCESS (time: {:.2f}s)".format(end_time - start_time))
            if i + batch_size < len(filepaths):
                time.sleep(max(0, 3 - (end_time - start_time)))
            
        except Exception as e: 
            end_time = time.time()
            print ("FAILED (time: {:.2f}s)".format(end_time - start_time))
            batch_dict['attempts'] += 1
            if batch_dict['attempts'] < 1:
                batched_filepaths.append(batch_dict)
            else:
                failed_instances.extend(batch)
    
    return simplified_names, failed_instances

def rename_webloc_files(simplified_names: Dict[str, str], dry_run: bool = False) -> None:
    """Rename .webloc files with their simplified names."""
    failed_instances = []
    for original_path, simplified_name in simplified_names.items():
        if not simplified_name:
            continue
            
        directory = os.path.dirname(original_path)
        original_name = os.path.basename(original_path)
        extension = os.path.splitext(original_name)[1]
        
        new_name = simplified_name + extension
        new_path = os.path.join(directory, new_name)
        
        # Check if the new filename is too long
        try:
            if len(new_name) > 255:
                print(f"Warning: New filename is too long ({len(new_name)} chars): {new_name}")
                new_name = new_name[:250] + extension
                new_path = os.path.join(directory, new_name)
                print(f"Truncated to: '{new_name}'")
            
            if dry_run:
                print(f"Would rename: '{original_name}' -> '{new_name}'")
            else:
                os.rename(original_path, new_path)
                print(f"Renamed: '{original_name}'\n      -> '{new_name}'")
        except Exception as e:
            failed_instances.append(original_path)
            print(f"Error renaming {original_name}: {e}")
    return failed_instances

def main():
    parser = argparse.ArgumentParser(description="Simplify filenames using OpenRouter API")
    parser.add_argument("--directory", "-d", default=".", help="Directory to search for files")
    parser.add_argument("--batch-size", "-b", type=int, default=50, help="Number of filenames to process in each API call")
    parser.add_argument("--api-key", "-k", help="OpenRouter API key (if not provided, will use OPENROUTER_API_KEY env var or prompt)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be renamed without actually renaming")
    args = parser.parse_args()
    
    # Get API key
    api_key = None
    try: 
        with open('credentials', 'r') as f:
            secrets = toml.load(f)
            api_key = secrets['OPENROUTER']['OPENROUTER_API_KEY']
    except: pass
    if (not api_key):
        api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            api_key = input("Enter your OpenRouter API key: ")
            if not api_key:
                print("API key is required.")
                sys.exit(1)
    
    # Find all .webloc files
    print(f"Searching for .webloc files in {args.directory}")
    valid_webloc_files = find_webloc_files(args.directory)
    if not valid_webloc_files:
        print("No valid .webloc files found.")
        return
    
    print(f"Found {len(valid_webloc_files)} valid .webloc files.")
    print(f"Simplifying filenames in batches of {args.batch_size} ...")
    simplified_names, failed_instances = simplify_filenames(valid_webloc_files, api_key, args.batch_size)
    
    # Display results
    if not simplified_names:
        print("No filenames were simplified. Check for API errors.")
        return
    
    print ("\nProposed name changes: ")
    for original_path, simplified_name in simplified_names.items():
        original_name = os.path.basename(original_path)
        print(f"    '{original_name}'\n -> '{simplified_name}'")
    
    # Confirm with user before renaming (unless dry run)
    if not args.dry_run:
        confirmation = input("\nProceed with renaming? (y/n): ")
        if confirmation.lower() != 'y':
            print("Operation cancelled.")
            return
    
    # Rename files
    failed_instances.extend(rename_webloc_files(simplified_names, args.dry_run))
    if len(failed_instances) > 0:
        print ("\nFailed instances: ")
        for instance in failed_instances: 
            print (instance)
        # write sample script to put all failed instances to the folder 'FAILED INSTANCES'
        script = f'''
import os
FAILED_LIST = {failed_instances}
FOLDER = 'FAILED_INSTANCE_FOLDER'
os.makedirs(FOLDER, exist_ok = True)
for instance in FAILED_LIST:
    os.rename(instance, os.path.join(FOLDER, os.path.basename(instance)))
        '''
        with open('failed.py', 'w') as f:
            f.write(script)
            f.close()

        print (f'''
Run 'python failed.py' to execute the following failed instance separation script: 
------------
{script}
------------
        ''')
    
    if args.dry_run:
        print("Dry run complete. No files were actually renamed.")
    else:
        print("Renaming complete. ")

if __name__ == "__main__": 
    main()
