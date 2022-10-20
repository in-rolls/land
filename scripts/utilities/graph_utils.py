# Graph utilities
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd

sns.set_theme(
    context="notebook",
    font_scale=1.05,
    style="whitegrid",
)  #  Darkgrid Whitegrid Dark White Ticks


def dotplot(
    data,
    x="count",
    y="nplots",
    xticks=None,
    labelsize=10,
    xlabel=None,
    title=None,
    savepath=None,
):
    nrows = len(data)
    _, ax = plt.subplots(figsize=(9, 9))
    sns.stripplot(x=x, y=y, data=data, orient="h", color="darkslategray", ax=ax)
    ax.set_ylim(nrows - 0.5, -0.5)
    sns.despine(left=True)
    if xticks:
        plt.xticks(xticks)
    plt.xlabel(xlabel, fontweight="bold")
    plt.ylabel("")
    ax.get_xaxis().set_major_formatter(
        ticker.FuncFormatter(lambda x, p: format(int(x), ","))
    )
    ax.tick_params(axis="y", labelsize=labelsize)

    def draw_alt_row_colors(ax, rowspan=5, color="0.5", alpha=0.1):
        yticks = ax.get_yticks()
        counter = 1
        for ix, _ in enumerate(yticks):
            if ix % rowspan == 0:
                if counter % 2 == 0:
                    ax.axhspan(
                        ix - 0.5, ix + rowspan - 0.5, color=color, alpha=alpha, zorder=0
                    )
                counter += 1
        return ax

    draw_alt_row_colors(ax)

    if title:
        plt.title(title, fontweight="bold", size=15, loc="left")

    if savepath:
        save_mpl_fig(savepath)
    return ax


def conbarplot(
    x,
    y,
    data,
    ci=95,
    xticklabels=None,
    title=None,
    grouplab=None,
    groups=None,
    annote_scaler=2,
    annotesize=11,
    titlesize=15,
    palette="cividis",
    alpha=0.7,
):
    """
    Plot 'connected' barplot by group
    """
    # Barplot
    ax = sns.barplot(
        x=x, y=y, data=data, ci=None, alpha=alpha, palette=palette, order=groups
    )

    # Plot points
    sns.pointplot(
        x=x,
        y=y,
        data=data,
        order=groups,
        ci=ci,
        capsize=None,
        join=False,
        errwidth=2,  # error bar width
        color=".3",
        ax=ax,
        zorder=1,
    )
    # Connect the points
    sns.pointplot(
        x=x,
        y=y,
        data=data,
        order=groups,
        ci=None,
        capsize=None,
        markers="",
        join=True,
        linestyles="--",
        errwidth=2,  # error bar width
        color=".4",
        zorder=0,
        ax=ax,
    )

    # Compute mean diff.
    if (grouplab is not None) and (groups is not None):
        group2 = data.query(f"{grouplab}=='{groups[1]}'")[y].mean()
        group1 = data.query(f"{grouplab}=='{groups[0]}'")[y].mean()
        diff = group2 - group1

        # Diff
        plt.text(
            x=1,
            y=group2 + annote_scaler,
            s=f"(Diff. = {diff:.1f})",
            ha="left",
            fontsize=annotesize,
        )

        # Group 1 mean
        plt.text(
            x=0,
            y=group1 + annote_scaler,
            s=f"{group1:.1f}",
            ha="left",
            fontsize=annotesize,
        )

    sns.despine(left=True)
    plt.ylabel("")
    plt.xlabel("")
    ax.yaxis.set_major_locator(plt.MaxNLocator(4))
    if xticklabels:
        ax.set_xticklabels(xticklabels)
    if title:
        plt.title(title, fontweight="bold", size=titlesize, loc="left")

    return ax


def save_mpl_fig(savepath):
    plt.savefig(f"{savepath}.pdf", dpi=None, bbox_inches="tight", pad_inches=0)
    plt.savefig(f"{savepath}.png", dpi=120, bbox_inches="tight", pad_inches=0)


def pandas_to_tex(df, texfile):
    if texfile.split(".")[-1] != ".tex":
        texfile += ".tex"
        
    tex_table = df.to_latex(index=False, header=False)
    tex_table_fragment = "\n".join(tex_table.split("\n")[2:-3])
    
    with open(texfile, "w") as tf:
        tf.write(tex_table_fragment)
    return None