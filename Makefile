DATA_DIR := data
# LF_DATA := $(DATA_DIR)/bihar_land_records_csv
FIGURE_DIR := figures
SCRIPTS_DIR := ./scripts
PY_UTILITIES := $(SCRIPTS_DIR)/utilities/utils.py
PY_GRAPH_UTILITIES := $(SCRIPTS_DIR)/utilities/graph_utils.py
EXECUTE_JUPYTERNB = cd $(SCRIPTS_DIR) && runpynb $(<F) 

$(NAMES_DATA): # Get unique ryot hindi names and caste
NAMES_DATA := $(DATA_DIR)/ryot_hindi_caste.csv.gz
$(NAMES_DATA): $(SCRIPTS_DIR)/get_ryot_hindi_caste.ipynb $(PY_UTILITIES)
	$(EXECUTE_JUPYTERNB)

$(HINDI_NAMES_RELIGION_DATA): # Get religion using pranaam and hindi names
HINDI_NAMES_RELIGION_DATA := $(DATA_DIR)/hindi_names_religion.csv.gz 
$(HINDI_NAMES_RELIGION_DATA): $(SCRIPTS_DIR)/get_religion.ipynb $(NAMES_DATA)
	@$(EXECUTE_JUPYTERNB) -t 5000

idata: # Build intermediate datasets
idata: $(NAMES_DATA) $(HINDI_NAMES_RELIGION_DATA)
.PHONY: idata

$(UNCOND_DIST): # Make the unconditional distribution plots
UNCOND_DIST := uncond_number_plots uncond_plot_area uncond_number_plots_dots
UNCOND_DIST := $(addprefix $(FIGURE_DIR)/, $(UNCOND_DIST)) 
UNCOND_DIST := $(addsuffix .png, $(UNCOND_DIST)) $(addsuffix .pdf, $(UNCOND_DIST)) 
$(UNCOND_DIST): $(SCRIPTS_DIR)/uncond_dist.ipynb $(PY_UTILITIES) $(PY_GRAPH_UTILITIES)
	$(EXECUTE_JUPYTERNB)

$(RELIGION_DIST): # Make distribution plots, by religion
RELIGION_DIST := religion_number_plots religion_barplot_plots religion_plot_area religion_barplot_plotarea
RELIGION_DIST := $(addprefix $(FIGURE_DIR)/, $(RELIGION_DIST)) 
RELIGION_DIST := $(addsuffix .png, $(RELIGION_DIST)) $(addsuffix .pdf, $(RELIGION_DIST)) 
$(RELIGION_DIST): $(SCRIPTS_DIR)/muslims_dist.ipynb $(PY_UTILITIES) $(PY_GRAPH_UTILITIES) $(HINDI_NAMES_RELIGION_DATA)
	$(EXECUTE_JUPYTERNB)

.PHONY: all
all: # Make everything
all: uplots idata religion_plots

.PHONY: uplots
uplots: # Make the unconditional plots
uplots: $(UNCOND_DIST)

.PHONY: religion_plots
religion_plots: # Make the religion plots
religion_plots: $(RELIGION_DIST)

.PHONY: build		
build: # Prepare data and figure folders if they do not exist
build: 
	mkdir -p $(DATA_DIR)
	mkdir -p $(FIGURE_DIR)

.PHONY: clean
clean: # Clean results in ./figures
# 	rm -f figures/*	
	rm -f $(RELIGION_DIST)
	rm -f $(UNCOND_DIST)
	rm -f $(NAMES_DATA) $(HINDI_NAMES_RELIGION_DATA)

.PHONY: help		
help: # Show Help
	@egrep -h '\s#\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?# "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
