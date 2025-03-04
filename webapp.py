import streamlit as st
import requests
import re
from requests.exceptions import RequestException
from cachetools import TTLCache

# Configuration
st.set_page_config(page_title="Biblical Truth Explorer", layout="wide")

# --- API Setup ---
API_KEY = "163cdbe0d16c4f6f51408959819d36c7"  # Use environment variables in production
HEADERS = {'api-key': API_KEY}
BIBLE_IDS = {
    "ESV": "06125adad2d5898a-01",
    "NIV": "111d4e367b7c8b49-01",
    "KJV": "179568874c45066f-01",
    "NASB": "0bc8833f3a4e1d2b-01"
}

# --- Caching ---
cache = TTLCache(maxsize=100, ttl=3600)  # Cache up to 100 items for 1 hour

# --- API Functions ---
def parse_reference(ref):
    """
    Parse a verse reference string (e.g., "John 3:16" or "Genesis 1:1-5") into book, chapter, and verse(s).
    Returns tuple: (book, chapter, verse_start, verse_end) or None if invalid.
    """
    pattern = r'([1-3]?\s?[A-Za-z]+)\s+(\d+):(\d+)(-(\d+))?'
    match = re.match(pattern, ref)
    if match:
        book = match.group(1).strip()
        chapter = int(match.group(2))
        verse_start = int(match.group(3))
        verse_end = int(match.group(5)) if match.group(5) else verse_start
        return book, chapter, verse_start, verse_end
    return None

def get_bible_text(book, chapter, verse_start, verse_end, translation):
    """
    Fetch Bible text from the API for a given book, chapter, and verse range.
    Returns tuple: (text, reference).
    """
    try:
        if translation == "Original Languages":
            return "Original language feature coming soon", ""
            
        bible_id = BIBLE_IDS.get(translation)
        if not bible_id:
            return "Translation not available", ""

        # Construct passage string (e.g., "John 3:16" or "Genesis 1:1-5")
        passage = f"{book} {chapter}:{verse_start}-{verse_end}" if verse_start != verse_end else f"{book} {chapter}:{verse_start}"
        cache_key = f"{bible_id}_{passage}"
        
        # Check cache first
        if cache_key in cache:
            return cache[cache_key]
        
        url = f"https://api.scripture.api.bible/v1/bibles/{bible_id}/search"
        params = {'query': passage}
        
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(data)
        if data['data']['verses']:
            # Combine text from multiple verses if a range is fetched
            text = ' '.join([v['text'] for v in data['data']['verses']])
            reference = f"{data['data']['verses'][0]['reference']}" if verse_start == verse_end else f"{book} {chapter}:{verse_start}-{verse_end}"
            cache[cache_key] = (text, reference)
            return text, reference
        return "Verse not found", passage
        
    except RequestException as e:
        return f"Network error: {str(e)}", ""
    except Exception as e:
        return f"API Error: {str(e)}", ""

# --- Interface ---
with st.sidebar:
    st.header("Search Parameters")
    
    # Allow users to choose between search modes
    search_mode = st.radio("Search Mode", ["By Reference", "By Book/Chapter/Verse"])
    
    if search_mode == "By Reference":
        ref = st.text_input("Enter verse reference (e.g., 'John 3:16' or 'Genesis 1:1-5')")
        if ref:
            parsed = parse_reference(ref)
            if parsed:
                book, chapter, verse_start, verse_end = parsed
            else:
                st.error("Invalid reference format. Use 'Book Chapter:Verse' or 'Book Chapter:Verse-Verse'")
                st.stop()
    else:
        book = st.selectbox("Book", ["Genesis", "Exodus", "Matthew", "John", "Revelation"])
        chapter = st.number_input("Chapter", 1, 150, 1)
        verse_start = st.number_input("Start Verse", 1, 176, 1)
        verse_end = st.number_input("End Verse", value=verse_start, min_value=verse_start, max_value=176)
    
    translation = st.selectbox("Translation", ["ESV", "NIV", "KJV", "NASB", "Original Languages"])

# Fetch the text based on search mode
if search_mode == "By Reference" and parsed:
    text, reference = get_bible_text(book, chapter, verse_start, verse_end, translation)
else:
    text, reference = get_bible_text(book, chapter, verse_start, verse_end, translation)

# Layout with adjusted column widths for mobile responsiveness
col1, col2 = st.columns([3, 2])

with col1:
    st.header("Biblical Text")
    
    if text.startswith("API Error") or text.startswith("Network error"):
        st.error(text)
    else:
        st.subheader(reference)
        st.write(text)
        st.caption(f"Translation: {translation}")

        if translation == "Original Languages":
            st.warning("Hebrew/Greek analysis coming in next version")

with col2:
    st.header("Analysis")
    
    with st.expander("Contextual Information"):
        st.write("""
        **Historical Background**: 
        - Date of writing: 1446-1406 BCE (traditional dating)
        - Cultural context: Ancient Near Eastern cosmology
        """)
        st.image("https://upload.wikimedia.org/wikipedia/commons/6/63/Codex_Sinaiticus_Matthew_6-7.jpg",
                caption="Ancient manuscript example")
    
    with st.expander("Textual Analysis"):
        st.write("""
        **Literary Features**:
        - Genre: Historical narrative
        - Key terms: "Create", "Beginning"
        """)
        
    with st.expander("Theological Significance"):
        st.write("""
        **Major Interpretations**:
        1. Literal creation account
        2. Theological manifesto
        3. Polemic against Canaanite myths
        """)

st.markdown("---")
st.caption("Note: Always verify findings with academic sources")