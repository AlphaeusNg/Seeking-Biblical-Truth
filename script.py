import os

# Define the paths
new_testament_path = r"D:\Life\ObsidianKB\Word of God\4. New Testament"
old_testament_path = r"D:\Life\ObsidianKB\Word of God\3. Old Testament"

# List of Bible books
old_testament_books = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi"
]

new_testament_books = [
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
    "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation"
]

def create_folders(path, books):
    for i, book in enumerate(books, start=1):
        folder_name = f"{i}. {book}"
        folder_path = os.path.join(path, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created: {folder_path}")
        else:
            print(f"Skipped (already exists): {folder_path}")

# Create folders
create_folders(old_testament_path, old_testament_books)
create_folders(new_testament_path, new_testament_books)
