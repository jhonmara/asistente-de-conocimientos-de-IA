import re
def chunk_text(text: str, chunk_size=800, overlap=120):
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = " ".join(tokens[i:i+chunk_size])
        chunks.append(chunk)
        i += max(1, chunk_size - overlap)
    return chunks
