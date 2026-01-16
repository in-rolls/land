### Unlanded: Distribution of Land in Bihar

Bihar, the third largest state in India, with over 100M people, is also its poorest---the GDP ppp is a mere $630. Agriculture constitues 23% of the economy which makes land ownership a vital source of income for many people.

Using the Bihar land records data---plot-level land records (N= 41.87 million plots or 12.13 individuals/accounts across 35,626 villages)---we describe the distribution of ownership of land, and how ownership varies by caste, religion, and gender. We also show ownership by last name and list top 10 land owning first and last names.

In particular, we investigate the distribution of a) the number of plots and b) total land area by `account number`. We also check how the ownership of land is distributed across castes and religion and using [naampy](https://github.com/appeler/naampy), we infer what proportion of land is registered to women. We compare these to the [base distribution](data/guesstimates.md).

## Data

* [data](data/)

## Scripts

All scripts are in [scripts/](scripts/).

### Summary & Comparisons

| Script | Purpose |
|--------|---------|
| `00_summary_basic_bihar_land_record.ipynb` | Basic summary stats of Bihar land records |
| `01_secc_gender_caste_proportions.ipynb` | SECC gender/caste proportions comparison |
| `02_plot_districts.ipynb` | District-level visualizations |

### Data Processing Pipeline

| Script | Purpose |
|--------|---------|
| `10_land_distribution_bihar.ipynb` | Core land distribution analysis |
| `20_get_ryot_hindi_caste.ipynb` | Extract unique names, assign caste codes |
| `30_get_religion.ipynb` | Infer religion using pranaam |
| `40_translate_hindi_to_english.ipynb` | Transliterate Hindi to English |
| `50_get_gender.ipynb` | Infer gender using naampy |
| `get_caste_outkast.ipynb` | Infer caste using outkast |

### Distribution Analysis

| Script | Purpose |
|--------|---------|
| `60_land_distribution_bihar_religion_coded.ipynb` | Distribution by religion |
| `61_land_distribution_bihar_gender.ipynb` | Distribution by gender |
| `61_land_distribution_bihar_religion_pranaam.ipynb` | Distribution by religion (pranaam) |
| `62_land_distribution_bihar_caste.ipynb` | Distribution by caste |
| `caste_outkast_dist.ipynb` | Caste distribution via outkast |
| `muslims_dist.ipynb` | Muslim population land distribution |
| `benchmark-ratio-viz.ipynb` | Benchmark comparisons |

### Geographic & Admin

| Script | Purpose |
|--------|---------|
| `crosswalk_district_block_village.ipynb` | Geographic hierarchy mapping |
| `merge_district_block_village.ipynb` | Merge administrative units |
| `flagged_land_accounts.ipynb` | Analysis of flagged accounts |

### LLM Annotation

Scripts in [scripts/llm_annotation/](scripts/llm_annotation/) for batch name classification via OpenAI API:

- `annotate_names_batch.py` - Batch annotation via OpenAI Batch API
- `annotate_names.py` - Streaming annotation with retry logic
- `schema.py` - Pydantic models for annotation responses
- `prompt.py` - System prompt for name classification

### Utilities

Scripts in [scripts/utilities/](scripts/utilities/):

- `utils.py` - Data loading and processing functions
- `graph_utils.py` - Visualization utilities

## Workflow

```bash
make setup   # Create venv and install dependencies
make idata   # Build intermediate datasets (caste, religion, gender)
make build   # Create data/figure directories
```

## Authors

Aaditya Dar, Lucas Shen, and Gaurav Sood
