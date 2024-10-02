from pdfminer.high_level import extract_text
import re
import os
import string

# Define regex patterns
formula_pattern = re.compile(r'[⇒→⇐⇔⇕⇖⇗⇘⇙⇚⇛⇜⇝⇞⇟=+∧*/^]|^\(\d+\.\d+\)$')
example_pattern = re.compile(r'\d+\.\d+\.\d+\s+EXAMPLE.*', flags=re.IGNORECASE)
equation_number_pattern = re.compile(r'^\(\d+\.\d+\)')
proposition_pattern = re.compile(r'Proposition\s+\d+\.\d+', flags=re.IGNORECASE)
bibliographic_notes_pattern = re.compile(r'^BIBLIOGRAPHIC NOTES', flags=re.IGNORECASE)
function_formula_pattern = re.compile(
    r'^¬?HoldsAt\(.*?\)$|^Happens\(.*?\)$|^¬?ReleasedAt\(.*?\)$|^Initiates\(.*?\)$|^Terminates\(.*?\)$|^¬?Releases\(.*?\)$Proposition$',
    flags=re.IGNORECASE
)

# Refined pattern for headers and footers
header_pattern = re.compile(r'^CHAPTER\s+\d+|^\d+\.\d+(?!\.\d+)(\s+[A-Za-z]+.*)?$')
footer_pattern = re.compile(r'^\d+\s*$')

def sanitize_filename(filename):
    # Replace colons with dashes
    filename = filename.replace(':', '-')
    # Remove invalid characters
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in filename if c in valid_chars)
    filename = filename.strip().replace(' ', '_')
    return filename

def process_example(example):
    title = example['title']
    raw_lines = example['raw_lines']
    lines = example['lines']
    
    # Remove empty lines from raw_lines
    raw_lines = [line for line in raw_lines if line.strip() != '']
    raw_text = '\n'.join(raw_lines)

    # Remove empty lines from lines
    lines = [line for line in lines if line.strip() != '']
    
    # Combine lines into paragraphs (processed text)
    paragraphs = []
    current_paragraph = ''
    
    for line in lines:
        # Handle hyphenated words at the end of a line
        if line.endswith('-'):
            current_paragraph += line[:-1]
        else:
            current_paragraph += line + ' '
            if line.endswith('.'):
                # End of a sentence, add the paragraph to the list
                paragraphs.append(current_paragraph.strip())
                current_paragraph = ''
    
    # Add any remaining text as a paragraph
    if current_paragraph:
        paragraphs.append(current_paragraph.strip())
    
    # Prepare the processed text to save
    text_to_save = '\n\n'.join(paragraphs)
    
    # Sanitize the filename
    filename = sanitize_filename(title) + '.txt'
    
    # Ensure the examples directory exists
    os.makedirs('examples', exist_ok=True)
    filepath = os.path.join('examples', filename)
    
    # Save the processed text to a file
    with open(filepath, 'w') as f:
        f.write(text_to_save)

    # Now save the raw text to 'raw texts' folder
    os.makedirs('raw texts', exist_ok=True)
    raw_filepath = os.path.join('raw texts', filename)

    # Save the raw text to a file
    with open(raw_filepath, 'w') as f:
        f.write(raw_text)

def parsing_text(text):
    ### For each chapter, extract examples and save them as separate text files
    
    # Initialize flags and variables
    is_example = False
    is_bibliographic_notes = False
    current_example = None

    for line in text.splitlines():
        stripped_line = line.strip()
        
        # Check for BIBLIOGRAPHIC NOTES
        if bibliographic_notes_pattern.search(stripped_line):
            is_bibliographic_notes = True
            break  # Stop processing further lines

        if is_bibliographic_notes:
            continue  # Skip processing lines after BIBLIOGRAPHIC NOTES

        # Check if the line indicates the start of an example section
        if example_pattern.search(stripped_line):
            is_example = True
            # If there is a current example, save it
            if current_example is not None:
                process_example(current_example)
            # Start a new example
            current_example = {'title': stripped_line, 'raw_lines': [], 'lines': []}
            continue

        # End the example section if "Proposition" or similar keywords are found
        if proposition_pattern.search(stripped_line):
            is_example = False
            if current_example is not None:
                process_example(current_example)
                current_example = None
            continue

        # Remove headers and footers based on the refined pattern
        if header_pattern.match(stripped_line) or footer_pattern.match(stripped_line):
            continue  # Skip headers and footers

        # If we are in an example section, collect both raw and processed lines
        if is_example and current_example is not None:
            # Collect raw lines
            current_example['raw_lines'].append(stripped_line)
            
            # Now apply filtering to decide whether to include in processed lines
            if (
                formula_pattern.search(stripped_line)
                or equation_number_pattern.search(stripped_line)
                or function_formula_pattern.search(stripped_line)
            ):
                continue  # Skip lines matching any of the patterns
            else:
                # Replace colons with periods and add the line to current example
                current_example['lines'].append(stripped_line.replace(':', '.'))

        # If the line seems to indicate the end of the example, stop capturing
        if re.match(r'^\d+\.\d+', stripped_line) and not re.search(r'EXAMPLE', stripped_line, flags=re.IGNORECASE):
            is_example = False
            if current_example is not None:
                process_example(current_example)
                current_example = None

    # After processing all lines, check if there is a current example
    if current_example is not None:
        process_example(current_example)
        current_example = None

if __name__ == '__main__':
    chapter_dir = 'Chapters/'
    files_paths = os.listdir(chapter_dir)
    files_paths.remove("Chapter-2---The-Event-Calculus_2015_Commonsense-Reasoning.pdf") ### Hardcoded to remove the file that is all formulas no examples.
    for file_path in files_paths:
        text = extract_text(os.path.join(chapter_dir, file_path))
        parsing_text(text)
        print(f'Processed {file_path}')
