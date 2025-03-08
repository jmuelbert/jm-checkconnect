import os

def calculate_translation_coverage(docs_dir):
    english_docs = set()
    translated_docs = {}  # {lang: set(filenames)}

    for root, _, files in os.walk(docs_dir):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                if "en" in filepath: # Assumes 'en' directory holds originals
                    english_docs.add(file)
                else:
                    # Extract language code (example: docs/fr/...)
                    try:
                        lang = root.split(os.sep)[1] # Get "fr" from "docs/fr"
                        if lang not in translated_docs:
                            translated_docs[lang] = set()
                        translated_docs[lang].add(file)
                    except:
                        pass # If language is not in the path skip it.

    total_docs = len(english_docs)
    translated_count = 0
    for lang, translated in translated_docs.items():
        translated_count += len(english_docs.intersection(translated)) # Number of english docs that are translated to this language.

    coverage = (translated_count / (len(translated_docs) * total_docs) ) * 100 if len(translated_docs) > 0 and total_docs > 0 else 0
    return coverage


if __name__ == "__main__":
    coverage = calculate_translation_coverage("docs")
    print(f"translation_coverage={coverage}")
