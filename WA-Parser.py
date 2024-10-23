import os
import json
import requests
import re
import yaml
from tqdm import tqdm
import logging
from urllib.parse import urljoin
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================== #
#        Configuration Load      #
# ============================== #

def load_config(config_path='config.yaml'):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' not found.")
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

config = load_config()

# ============================== #
#         Setup Logging          #
# ============================== #

logging.basicConfig(
    level=logging.DEBUG if config.get('DEBUG', False) else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# ============================== #
#        Directory Setup         #
# ============================== #

source_directory = config.get('source_directory', 'World-Anvil-Export')
destination_directory = config.get('destination_directory', 'World-Anvil-Output')
obsidian_resource_folder = config.get('obsidian_resource_folder', 'images')

# Ensure necessary directories exist
os.makedirs(destination_directory, exist_ok=True)
os.makedirs(obsidian_resource_folder, exist_ok=True)

# ============================== #
#           Helper Functions     #
# ============================== #

def safe_get(d, keys, default=None):
    """
    Safely get a nested value from a dictionary.
    """
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d if d is not None else default

def extract_image_urls(data, pattern):
    """
    Extract all image URLs from the JSON data based on the provided regex pattern.
    """
    image_urls = set()

    def search_images(obj):
        if isinstance(obj, dict):
            for value in obj.values():
                search_images(value)
        elif isinstance(obj, list):
            for item in obj:
                search_images(item)
        elif isinstance(obj, str):
            matches = re.findall(pattern, obj)
            for match in matches:
                image_urls.add(match)

    search_images(data)
    return image_urls

def setup_session():
    """
    Setup a requests session with retry strategy.
    :return: Configured requests session.
    """
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,  # Increased backoff factor for exponential backoff
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]  # Correct parameter name
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # Add User-Agent header and keep-alive
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; WA-Parser/1.0)',
        'Connection': 'keep-alive'
    })
    return session

def download_image(url, dest_folder, session):
    """
    Download an image from a URL to the destination folder.
    """
    try:
        response = session.get(url, stream=True, timeout=30)  # Increased timeout to 30 seconds
        if response.status_code == 404:
            logging.warning(f"Image not found (404): {url}")
            return
        response.raise_for_status()
        filename = os.path.basename(url)
        # Handle query parameters in filename
        filename = filename.split('?')[0]
        filepath = os.path.join(dest_folder, filename)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        logging.debug(f"Downloaded image: {filename}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download image {url}. Error: {e}")

def format_content(content, attempt_bbcode=True):
    """
    Format the content by replacing BBCode and other markup with Markdown.
    """
    if not content:
        return ""
    text = content.get('text', '')
    if not isinstance(text, str):
        return str(text)

    # Replace World Anvil links with Obsidian internal links
    text = re.sub(r'@\[([^\]]+)\]\([^)]+\)', r'[[\1]]', text)
    text = re.sub(r'\r\n\r', r'\n', text)  # Fix extra spacing

    if attempt_bbcode:
        text = re.sub(r'[ \t]+', ' ', text)  # Strip extra spaces and tabs
        text = re.sub(r'\n +(\[h\d\])', r'\n\1', text)  # Remove leading spaces before headings
        text = re.sub(r'\[br\]', r'\n', text)  # [br] to newline

        # Heading conversions
        for i in range(1, 5):
            text = re.sub(rf'\[h{i}\](.*?)\[/h{i}\]', f'{"#"*i} \\1', text)

        # Other BBCode conversions
        bbcode_patterns = {
            r'\[p\](.*?)\[/p\]': r'\1\n',
            r'\[b\](.*?)\[/b\]': r'**\1**',
            r'\[i\](.*?)\[/i\]': r'*\1*',
            r'\[u\](.*?)\[/u\]': r'<u>\1</u>',
            r'\[s\](.*?)\[/s\]': r'~~\1~~',
            r'\[url\](.*?)\[/url\]': r'[\1](\1)',
            r'\[list\](.*?)\[/list\]': lambda m: re.sub(r'\[\*\](.*?)\n?', r'* \1\n', m.group(1), flags=re.DOTALL),
            r'\[code\](.*?)\[/code\]': r'```\n\1\n```',
            r'\[quote\]([\s\S]*?)\[/quote\]': lambda m: '\n> '.join(m.group(1).split('\n')),
            r'\[sup\](.*?)\[/sup\]': r'<sup>\1</sup>',
            r'\[sub\](.*?)\[/sub\]': r'<sub>\1</sub>',
            r'\[ol\]|\[/ol\]': '',
            r'\[ul\]|\[/ul\]': '',
            r'\[li\](.*?)\[/li\]': r'* \1',
        }

        for pattern, repl in bbcode_patterns.items():
            text = re.sub(pattern, repl, text, flags=re.DOTALL)

    return text

def extract_sections(data):
    """
    Extract extra sections from the data.
    """
    sections = data.get("sections")
    extracted = []
    if isinstance(sections, dict):
        for section_key, section_data in sections.items():
            if isinstance(section_data, dict):
                content = section_data.get("content", "")
                if isinstance(content, str) and content.strip():
                    section_content = format_content({'text': content})
                    section_key_formatted = ' '.join(section_key.split('_')).title()
                    extracted.append((section_key_formatted, section_content))
    return extracted

def extract_relations(data):
    """
    Extract relations from the data.
    """
    relations = data.get("relations")
    extracted = []
    if isinstance(relations, dict):
        for relation_key, relation_data in relations.items():
            if isinstance(relation_data, dict):
                items = relation_data.get("items")
                if not items:
                    continue
                content = ''
                if isinstance(items, list):
                    for item in items:
                        relationship_type = item.get("relationshipType", "")
                        title = item.get("title", "")
                        if relationship_type.lower() == "article":
                            content += f'[[{title}]]\n'
                        else:
                            content += f'{title}\n'
                elif isinstance(items, dict):
                    title = items.get("title", "")
                    content = f"[[{title}]]"
                if content:
                    relation_key_formatted = ' '.join(relation_key.split('_')).title()
                    extracted.append((relation_key_formatted, content))
    return extracted

# ============================== #
#         Image Downloading      #
# ============================== #

def download_all_images(image_urls, dest_folder):
    """
    Download all images concurrently with retry mechanism.
    """
    session = setup_session()
    max_workers = 4  # Reduced from 10 to 4 to prevent server overload
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(download_image, url, dest_folder, session)
            for url in image_urls
        ]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Downloading Images", disable=not config.get('DEBUG', False)):
            pass  # All logging is handled in download_image

# ============================== #
#         Main Execution         #
# ============================== #

def main():
    # Initialize counters
    success_count = 0
    failure_count = 0
    total_files = 0

    # Collect all image URLs to download later
    all_image_urls = set()

    # First pass: Collect image URLs from all JSON files
    for root, dirs, files in os.walk(source_directory):
        for filename in files:
            if filename.endswith('.json'):
                total_files += 1
                json_file = os.path.join(root, filename)
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except json.JSONDecodeError as json_err:
                    logging.error(f"JSON decode error in file {json_file}: {json_err}")
                    failure_count += 1
                    continue
                except Exception as e:
                    logging.error(f"Error reading file {json_file}: {e}")
                    failure_count += 1
                    continue

                # Extract image URLs from content
                image_pattern = config.get('image_search_pattern', '/uploads/images/[a-zA-Z0-9./_-]+')
                image_urls = extract_image_urls(data, image_pattern)
                # Prepend base_url to relative URLs
                base_url = config.get('base_url', 'https://worldanvil.com')
                full_image_urls = set()
                for url in image_urls:
                    if url.startswith('http://') or url.startswith('https://'):
                        full_url = url
                    else:
                        full_url = urljoin(base_url, url)
                    full_image_urls.add(full_url)
                all_image_urls.update(full_image_urls)

    logging.info(f"Total JSON files found: {total_files}")
    logging.info(f"Total unique images to download: {len(all_image_urls)}")

    # Download all images
    if all_image_urls:
        download_all_images(all_image_urls, obsidian_resource_folder)

    # Initialize progress bar for processing articles
    progress_bar = tqdm(total=total_files, unit=' articles', desc='Processing', ncols=100)

    # Second pass: Process each JSON file and create Markdown
    for root, dirs, files in os.walk(source_directory):
        for filename in files:
            if filename.endswith('.json'):
                json_file = os.path.join(root, filename)
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except json.JSONDecodeError as json_err:
                    logging.error(f"JSON decode error in file {json_file}: {json_err}")
                    failure_count += 1
                    progress_bar.update(1)
                    continue
                except Exception as e:
                    logging.error(f"Error reading file {json_file}: {e}")
                    failure_count += 1
                    progress_bar.update(1)
                    continue

                try:
                    # Extracting data to use as yaml metadata in the Obsidian document
                    creation_date = safe_get(data, ["creationDate", "date"], "")
                    world_title = safe_get(data, ["world", "title"], "")

                    yaml_data = {
                        "creationDate": creation_date,
                        "template": data.get("template", ""),
                        "world": world_title,
                    }

                    # Create a subfolder based on the template
                    template = yaml_data.get("template", "other")
                    template_folder = os.path.join(destination_directory, template)
                    os.makedirs(template_folder, exist_ok=True)

                    # Create a Markdown file in the destination directory
                    markdown_filename = os.path.join(template_folder, os.path.splitext(filename)[0] + '.md')
                    with open(markdown_filename, 'w', encoding='utf-8') as markdown_file:

                        # Writing the metadata yaml
                        markdown_file.write('---\n')
                        yaml.dump(yaml_data, markdown_file, sort_keys=False, allow_unicode=True)
                        markdown_file.write('---\n\n')

                        # Writing the main content
                        for tag in config.get('content_tags_to_extract', ['title', 'content']):
                            value = data.get(tag, '')
                            if tag == 'content':
                                formatted_content = format_content({'text': value}, config.get('attempt_bbcode', True))
                                markdown_file.write(f"{formatted_content}\n\n")
                            elif value:
                                markdown_file.write(f"# {tag.capitalize()}: {value}\n\n")  # This creates a L1 header based on the tag

                        markdown_file.write("# Extras\n\n")  # Change this if you want to change the extras L1 header

                        # Extract extra sections, create L2 headers and put their content below
                        sections = extract_sections(data)
                        for section_header, section_content in sections:
                            markdown_file.write(f"## {section_header}\n\n{section_content}\n")

                        # Extract relations, create L2 headers and put their content below
                        relations = extract_relations(data)
                        for relation_header, relation_content in relations:
                            markdown_file.write(f"## {relation_header}\n\n{relation_content}\n")

                    success_count += 1

                except Exception as e:
                    logging.error(f"Failed to convert {json_file}. Error: {e}")
                    failure_count += 1

                finally:
                    progress_bar.update(1)

    progress_bar.close()
    logging.info(f"WA-Parser is finished. Successfully converted {success_count} articles with {failure_count} failures. Please validate your results.")

if __name__ == '__main__':
    main()
