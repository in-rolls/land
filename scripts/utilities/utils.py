import pandas as pd
import janitor
import os
import gc
# Graph utilities
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
sns.set_theme(context="notebook", font_scale=1.05, 
			  style='whitegrid')  #  Darkgrid Whitegrid Dark White Ticks


def get_fulldata(directory='../data/bihar_land_records_csv/', **pandas_kwargs):
	final_df = []
	for filename in os.listdir(directory):
		f = os.path.join(directory, filename)
		lr_file = pd.read_csv(f, low_memory=False, **pandas_kwargs)
		#lr_file_dedupe = lr_file.drop_duplicates(subset=['account_no'])
		final_df.append(lr_file)

	final_frame = pd.concat(final_df, axis=0, ignore_index=True)
	del final_df
	gc.collect()

	return final_frame


def dotplot(data, x='count', y='nplots', xticks=None, title=None, savepath=None):
	nrows = len(data)
	_, ax = plt.subplots(figsize=(9,9))
	sns.stripplot(x=x, y=y, data=data, 
				  orient='h', color='darkslategray', ax=ax)
	ax.set_ylim(nrows-.5, -.5)
	sns.despine(left=True)
	if xticks:
		plt.xticks(xticks)
	plt.xlabel('Accounts', fontweight='bold')
	plt.ylabel('')
	ax.get_xaxis().set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
	ax.tick_params(axis='y', labelsize=10)
	def draw_alt_row_colors(ax, rowspan=5, color='0.5', alpha=0.1):
		yticks = ax.get_yticks()
		counter = 1
		for ix, _ in enumerate(yticks):
			if ix%rowspan==0:
				if counter%2==0:
					ax.axhspan(ix-.5, ix+rowspan-.5, color=color, alpha=alpha, zorder=0)
				counter += 1
		return ax
	draw_alt_row_colors(ax)
	
	if title:
		plt.title(title, fontweight='bold', size=15, loc='left')

	if savepath:
		save_mpl_fig(savepath)
	return ax	


def save_mpl_fig(savepath):
	plt.savefig(f'{savepath}.pdf', dpi=None, bbox_inches='tight', pad_inches=0)
	plt.savefig(f'{savepath}.png', dpi=120, bbox_inches='tight', pad_inches=0)    