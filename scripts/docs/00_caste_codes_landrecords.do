* prepare caste codes for the land records data

* prelim 
clear all 
global path "C:/Users/aadit/Arthashala Dropbox/"
global github "C:/Users/aadit/Documents/GitHub/caste"

* read amisha's data 
import excel "$path/Aaditya Dar/research/bihar_jati/land_records/unique_castes_all_districts_amisha.xlsx", sheet("Sheet1") firstrow clear 
keep caste count caste_translit caste_standard

* save to temp file 
tempfile usingf_a
save `usingf_a'

* read arjun's data
import excel "$path/Aaditya Dar/research/bihar_jati/land_records/unique_castes_all_districts_arjun.xlsx", sheet("Sheet1") firstrow clear
keep caste count caste_translit caste_standard

* append 
append using `usingf_a'

* clean strings
strstd 

* mop up 
drop if caste_standard == ""
rename caste caste_landrecords 

* standardize caste names
clonevar caste_name = caste_standard

replace caste_name = "bhumihar" if inlist(caste_standard, "bumihar", "bahban") // spelling variation
replace caste_name = "brahmin" if caste_standard == "brahman" // spelling variation
replace caste_name = "chamar" if inlist(caste_standard, "chaamar", "chamaar") // spelling variation
replace caste_name = "chandravanshi" if inlist(caste_standard, "chanadaravashi", "chandaravashi", "chandravar", "chandravashi") // spelling variation
replace caste_name = "dusad" if caste_standard == "dusadh" // spelling variation
replace caste_name = "musahar" if inlist(caste_standard, "majhi", "manjhi") // alternative name
replace caste_name = "nai" if inlist(caste_standard, "hajam", "hajjam") // alternative name https://en.wikipedia.org/wiki/Hajjam
replace caste_name = "pan" if caste_standard == "tattama" // alternative name https://en.wikipedia.org/wiki/tattama
replace caste_name = "yadav" if caste_standard == "gop" // spelling variation
replace caste_name = "rajput" if caste_standard == "thakur" // Anthropologists say Thakurs and Rajputs are almost synonymous with each other. https://indianexpress.com/article/research/how-the-thakurs-have-dominated-up-politics-since-independence-yogi-adityanath-6717581/

* merge castes 
merge m:1 caste_name using ///
"$github/input/caste_codes/caste_dictionary_n292.dta", gen(m_cc)

tab m_cc [aw = count]
tab caste_name if m_cc == 1 [aw = count], sort

drop if m_cc != 3 
gsort -count

save "$github/input/caste_codes/caste_code_landrecords.dta", replace 
