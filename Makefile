.DEFAULT_GOAL := help

DATA_DIR := data
# LF_DATA := $(DATA_DIR)/bihar_land_records_csv
FIGURE_DIR := figures
SCRIPTS_DIR := ./scripts
PY_UTILITIES := $(SCRIPTS_DIR)/utilities/utils.py
PY_GRAPH_UTILITIES := $(SCRIPTS_DIR)/utilities/graph_utils.py
EXECUTE_JUPYTERNB = cd $(SCRIPTS_DIR) && runpynb $(<F) 

# ============================================================================
# Intermediate Data: Going from the raw Bihar land records to intermediate
# data (e.g., account holder names with gender, religion, castes)
# ============================================================================
$(NAMES_DATA): # Get unique ryot hindi names and caste
NAMES_DATA := $(DATA_DIR)/ryot_hindi_caste.csv.gz
$(NAMES_DATA): $(SCRIPTS_DIR)/get_ryot_hindi_caste.ipynb $(PY_UTILITIES)
	$(EXECUTE_JUPYTERNB)

$(HINDI_NAMES_RELIGION_DATA): # Get religion using pranaam and hindi names
HINDI_NAMES_RELIGION_DATA := $(DATA_DIR)/hindi_names_religion.csv.gz 
$(HINDI_NAMES_RELIGION_DATA): $(SCRIPTS_DIR)/get_religion.ipynb $(NAMES_DATA)
	@$(EXECUTE_JUPYTERNB) -t 10000

TRANSLATED_NAMES_DATA := $(DATA_DIR)/hindi_names_religion_translated.csv.gz

$(HINDI_ENG_NAMES_GENDER_DATA): # Get gender using naampy and english names
HINDI_ENG_NAMES_GENDER_DATA := $(DATA_DIR)/hindi_eng_names_gender.csv.gz
$(HINDI_ENG_NAMES_GENDER_DATA): $(SCRIPTS_DIR)/get_gender.ipynb $(TRANSLATED_NAMES_DATA)
	@$(EXECUTE_JUPYTERNB) 

$(HINDI_ENG_NAMES_OUTKAST_DATA): # Get caste using outkast and english names
HINDI_ENG_NAMES_OUTKAST_DATA := $(DATA_DIR)/hindi_eng_names_caste_outkast.csv.gz
$(HINDI_ENG_NAMES_OUTKAST_DATA): $(SCRIPTS_DIR)/get_caste_outkast.ipynb $(TRANSLATED_NAMES_DATA)
	@$(EXECUTE_JUPYTERNB) 	

idata: # Build intermediate datasets
INTERMEDIATE_DATA := $(NAMES_DATA) $(HINDI_NAMES_RELIGION_DATA) $(HINDI_ENG_NAMES_OUTKAST_DATA) $(HINDI_ENG_NAMES_GENDER_DATA)
idata: $(INTERMEDIATE_DATA)
.PHONY: idata


# ============================================================================
# Main results: For main figures and tables
# ============================================================================
# $(UNCOND_DIST): # Make the unconditional distribution plots
# UNCOND_DIST := uncond_number_plots uncond_plot_area uncond_number_plots_dots
# UNCOND_DIST := $(addprefix $(FIGURE_DIR)/, $(UNCOND_DIST)) 
# UNCOND_DIST := $(addsuffix .png, $(UNCOND_DIST)) $(addsuffix .pdf, $(UNCOND_DIST)) 
# $(UNCOND_DIST): $(SCRIPTS_DIR)/uncond_dist.ipynb $(PY_UTILITIES) $(PY_GRAPH_UTILITIES)
# 	$(EXECUTE_JUPYTERNB)

# $(RELIGION_DIST): # Make distribution plots, by religion
# RELIGION_DIST := religion_number_plots religion_barplot_plots religion_plot_area religion_barplot_plotarea
# RELIGION_DIST := $(addprefix $(FIGURE_DIR)/, $(RELIGION_DIST)) 
# RELIGION_DIST := $(addsuffix .png, $(RELIGION_DIST)) $(addsuffix .pdf, $(RELIGION_DIST)) 
# $(RELIGION_DIST): $(SCRIPTS_DIR)/muslims_dist.ipynb $(PY_UTILITIES) $(PY_GRAPH_UTILITIES) $(HINDI_NAMES_RELIGION_DATA)
# 	$(EXECUTE_JUPYTERNB)

# $(GENDER_DIST): # Make distribution plots, by gender 
# GENDER_DIST := gender_number_plots gender_barplot_plots gender_plot_area gender_barplot_plotarea
# GENDER_DIST := $(addprefix $(FIGURE_DIR)/, $(GENDER_DIST)) 
# GENDER_DIST := $(addsuffix .png, $(GENDER_DIST)) $(addsuffix .pdf, $(GENDER_DIST)) 
# $(GENDER_DIST): $(SCRIPTS_DIR)/gender_dist.ipynb $(PY_UTILITIES) $(PY_GRAPH_UTILITIES) $(HINDI_ENG_NAMES_GENDER_DATA)
# 	$(EXECUTE_JUPYTERNB)

# $(CASTE_OUTKAST_DIST): # Make distribution plots, by caste 
# CASTE_OUTKAST_DIST := castes_outkast_number_plots castes_outkast_barplot_plots castes_outkast_plot_area castes_outkast_barplot_plotarea
# CASTE_OUTKAST_DIST := $(addprefix $(FIGURE_DIR)/, $(CASTE_OUTKAST_DIST)) 
# CASTE_OUTKAST_DIST := $(addsuffix .png, $(CASTE_OUTKAST_DIST)) $(addsuffix .pdf, $(CASTE_OUTKAST_DIST)) 
# $(CASTE_OUTKAST_DIST): $(SCRIPTS_DIR)/caste_outkast_dist.ipynb $(PY_UTILITIES) $(PY_GRAPH_UTILITIES) $(HINDI_ENG_NAMES_GENDER_DATA)
# 	$(EXECUTE_JUPYTERNB)

# .PHONY: all
# all: # Make everything
# all: uplots idata religion_plots gender_plots caste_outkast_plots

# .PHONY: uplots
# uplots: # Make the unconditional plots
# uplots: $(UNCOND_DIST)

# .PHONY: religion_plots
# religion_plots: # Make the religion plots
# religion_plots: $(RELIGION_DIST)

# .PHONY: gender_plots
# gender_plots: # Make the gender plots
# gender_plots: $(GENDER_DIST)

# .PHONY: caste_outkast_plots
# caste_outkast_plots: # Make the caste (via outkast) plots
# caste_outkast_plots: $(CASTE_OUTKAST_DIST)		

.PHONY: build		
build: # Prepare data and figure folders if they do not exist
build: 
	mkdir -p $(DATA_DIR)
	mkdir -p $(FIGURE_DIR)

# ============================================================================
# Set up the Python virtual environment and prepare the Jupyter distribution
# Installs packages from requirements.txt
# ============================================================================
.PHONY: setup
setup: # Set up venv	
setup: requirements.txt
	@echo "==> $@"
	@echo "==> Creating and initializing virtual environment..."
	rm -rf venv_land
	python -m venv venv_land
	. venv_land/bin/activate && \
		pip install --upgrade pip && \
		which pip && \
		pip list && \
		echo "==> Installing requirements" && \
		pip install -r $< && \
		jupyter contrib nbextensions install --sys-prefix --skip-running-check && \
		echo "==> Packages available:" && \
		which pip && \
		pip list && \
		which jupyter && \
		deactivate
	@echo "==> Setup complete."


# ============================================================================
# Additional utilities
# ============================================================================
.PHONY: clean
clean: # Clean results in ./figures
# 	rm -f figures/*	
	rm -f $(GENDER_DIST) 
	rm -f $(CASTE_OUTKAST_DIST) 
	rm -f $(RELIGION_DIST)
	rm -f $(UNCOND_DIST)
	rm -f $(INTERMEDIATE_DATA)

.PHONY: help		
help: # Show Help
	@egrep -h '\s#\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?# "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'