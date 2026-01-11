import pandas as pd
from indicate import transliterate
from tqdm import tqdm
import warnings
import sys
warnings.filterwarnings('ignore')

INPUT_FILE = '../data/hindi_names_religion.csv.gz'

print(f"Loading data from {INPUT_FILE}...")
df = pd.read_csv(INPUT_FILE, compression='gzip')
print(f"Loaded {len(df)} rows")

cache = {}
def hin_to_eng(name):
    words = []
    for word in str(name).split():
        if word not in cache:
            cache[word] = transliterate.hindi2english(word)
        words.append(cache[word])
    return ' '.join(words).strip()

print("Starting transliteration...")
tqdm.pandas()
df['eng_name'] = df['name'].progress_apply(hin_to_eng)

print("Saving results...")
df.to_parquet("../data/hindi_names_religion_translated.parquet", index=False)
