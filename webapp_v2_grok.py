import json
from pathlib import Path

# Constants
BIBLE_JSON = 'bible_repo\holybooks\EN'  # Bible data file in your project folder
OUTPUT_DIR = Path('site')  # Directory for generated site
OUTPUT_DIR.mkdir(exist_ok=True)

# HTML Templates as strings
CHAPTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>{book} {chapter}</h1>
    <div class="verses">
        {verses_html}
    </div>
    <nav>
        <a href="{prev_link}">Previous</a> | 
        <a href="index.html">Home</a> | 
        <a href="{next_link}">Next</a>
    </nav>
</body>
</html>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bible Study</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>Pursuit of Biblical Truth</h1>
    <p>Select a book to begin:</p>
    <ul class="book-list">
        {books_html}
    </ul>
</body>
</html>
"""

CSS = """
body {
    font-family: Arial, sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}
.verses p { margin: 5px 0; }
nav { margin-top: 20px; }
.book-list { list-style: none; padding: 0; }
.book-list li { margin: 5px 0; }
"""

# Functions
def load_bible_data():
    """Load Bible data from JSON file."""
    with open(BIBLE_JSON, 'r') as f:
        return json.load(f)

def generate_verses_html(verses):
    """Convert verses to HTML paragraphs."""
    return ''.join(f'<p><strong>{v["verse"]}</strong> {v["text"]}</p>' for v in verses)

def get_prev_next_links(book_idx, chapter_idx, bible):
    """Generate previous and next navigation links."""
    books = bible['books']
    book = books[book_idx]
    prev_link = next_link = '#'
    
    # Previous link
    if chapter_idx > 1:
        prev_link = f'{book["name"]}_{chapter_idx-1}.html'
    elif book_idx > 0:
        prev_book = books[book_idx-1]
        prev_link = f'{prev_book["name"]}_{len(prev_book["chapters"])}.html'
    
    # Next link
    if chapter_idx < len(book['chapters']):
        next_link = f'{book["name"]}_{chapter_idx+1}.html'
    elif book_idx < len(books) - 1:
        next_link = f'{books[book_idx+1]["name"]}_1.html'
    
    return prev_link, next_link

def generate_chapter_pages(bible):
    """Generate HTML files for each chapter."""
    for book_idx, book in enumerate(bible['books']):
        for chapter_idx, chapter in enumerate(book['chapters'], start=1):
            verses_html = generate_verses_html(chapter['verses'])
            prev_link, next_link = get_prev_next_links(book_idx, chapter_idx, bible)
            html = CHAPTER_TEMPLATE.format(
                title=f'{book["name"]} {chapter["chapter"]}',
                book=book['name'],
                chapter=chapter['chapter'],
                verses_html=verses_html,
                prev_link=prev_link,
                next_link=next_link
            )
            file_path = OUTPUT_DIR / f'{book["name"]}_{chapter["chapter"]}.html'
            with open(file_path, 'w') as f:
                f.write(html)

def generate_index_page(bible):
    """Generate the index page with book links."""
    books_html = ''.join(
        f'<li><a href="{book["name"]}_1.html">{book["name"]}</a></li>'
        for book in bible['books']
    )
    html = INDEX_TEMPLATE.format(books_html=books_html)
    with open(OUTPUT_DIR / 'index.html', 'w') as f:
        f.write(html)

def write_static_files():
    """Write CSS and other static files."""
    with open(OUTPUT_DIR / 'style.css', 'w') as f:
        f.write(CSS)

def main():
    """Main function to generate the website."""
    bible = load_bible_data()
    write_static_files()
    generate_chapter_pages(bible)
    generate_index_page(bible)
    print(f"Website generated in {OUTPUT_DIR}. Upload this folder to GitHub Pages.")

if __name__ == '__main__':
    main()