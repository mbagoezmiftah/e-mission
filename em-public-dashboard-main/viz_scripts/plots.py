import pandas as pd
import numpy as np
import arrow
import itertools
import matplotlib.pyplot as plt
import seaborn as sns
import traceback as tb
from matplotlib.patches import Patch

sns.set_style("whitegrid")
sns.set()
get_ipython().run_line_magic('matplotlib', 'inline')

# Module for pretty-printing outputs (e.g. head) to help users
# understand what is going on
# However, this means that this module can only be used in an ipython notebook

import IPython.display as disp


SAVE_DIR="/plots/"

def calculate_pct(labels, values):
    v2l_df = pd.DataFrame({"vals": values}, index=labels)

    # Calculate % for all the values
    vs = v2l_df.vals.sum()
    v2l_df["pct"] = v2l_df.vals.apply(lambda x: round((x/vs) * 100, 1))

    return (v2l_df.index.to_list(),v2l_df.vals.to_list(), v2l_df.pct.to_list())

def merge_small_entries(labels, values):
    v2l_df = pd.DataFrame({"vals": values}, index=labels)

    # Calculate % for all the values
    vs = v2l_df.vals.sum()
    v2l_df["pct"] = v2l_df.vals.apply(lambda x: round((x/vs) * 100, 1))
    disp.display(v2l_df)

    # Find small chunks to combine
    small_chunk = v2l_df.where(lambda x: x.pct <= 2).dropna()
    misc_count = small_chunk.sum()

    v2l_df = v2l_df.drop(small_chunk.index)
    disp.display(v2l_df)

    # we need to let the sensed be "OTHER" and labeled or inferred be "Other"
    # going to use capitalization as a flag
    if v2l_df.index[0][-1].isupper():
        print("Found uppercase last letter")
        # This part if a bit tricky
        # We could have already had a non-zero other, and it could be small or large
        if "OTHER" not in v2l_df.index:
            # zero other will end up with misc_count
            if misc_count.vals > 0:
                v2l_df.loc["OTHER"] = misc_count
        elif "OTHER" in small_chunk.index:
            # non-zero small other will already be in misc_count
            v2l_df.loc["OTHER"] = misc_count
        else:
            # non-zero large other, will not already be in misc_count
            v2l_df.loc["OTHER"] = v2l_df.loc["OTHER"] + misc_count
    else: #assuming labeled or inferred
        # This part if a bit tricky
        # We could have already had a non-zero other, and it could be small or large
        if "other" not in v2l_df.index:
            # zero other will end up with misc_count
            if misc_count.vals > 0:
                v2l_df.loc["other"] = misc_count
        elif "other" in small_chunk.index:
            # non-zero small other will already be in misc_count
            v2l_df.loc["other"] = misc_count
        else:
            # non-zero large other, will not already be in misc_count
            v2l_df.loc["other"] = v2l_df.loc["other"] + misc_count
    
    disp.display(v2l_df)

    return (v2l_df.index.to_list(),v2l_df.vals.to_list(), v2l_df.pct.to_list())

# Create dataframes with cols: 'Label' 'Value' and 'Proportion'
def process_trip_data(labels, values):
    """ Inputs:
    labels = Displayed labels (e.g. "Gas car, drove alone")
    values = Corresponding vlaues of these labels
    trip_type = Bar labels (e.g. Labeled by user (Confirmed trips))
    Returns:
    df_total_trip_expanded = Data frame without consolidation of Others, used to create the alt_html table
    df_total_trip = Data frame with consolidation of Others, used to represent the Bar Charts.
    """
    if len(labels) == 0 and len(values) == 0:
        return pd.DataFrame(), pd.DataFrame()
    m_labels_expanded, m_values_expanded, m_pct_expanded = calculate_pct(labels, values)
    data_trip_expanded = {'Label': m_labels_expanded, 'Value': m_values_expanded, 'Proportion': m_pct_expanded}
    df_total_trip_expanded = pd.DataFrame(data_trip_expanded)

    m_labels, m_values, m_pct = merge_small_entries(labels, values)
    data_trip = {'Label': m_labels, 'Value': m_values, 'Proportion': m_pct}
    df_total_trip = pd.DataFrame(data_trip)
    return df_total_trip_expanded, df_total_trip

def plot_and_text_error(e, ax, file_name):
    stringified_exception = "".join(tb.format_exception(type(e), e, e.__traceback__))
    ax.text(0,0,s=stringified_exception)
    plt.savefig(SAVE_DIR+file_name+".png", bbox_inches='tight')
    alt_text = f"Error while generating chart:"
    alt_text += stringified_exception
    alt_text = access_alt_text(alt_text, file_name)
    # TODO: Format the error as HTML instead of plain text
    alt_html = access_alt_html(alt_text, file_name)
    return alt_text, alt_html

# Creates/ Appends single bar to the 100% Stacked Bar Chart
def plot_and_text_stacked_bar_chart(df, agg_fcn, bar_label, ax, text_result, colors, debug_df, values_to_translations={}):
    """ Inputs:
    df = Data frame corresponding to the bar in a stacked bar chart. It is
        expected to have three columns, which represent the 'label', 'value'
    bar_label = Text to represent the Bar (e.g. Labeled by user\n (Confirmed trips))
    ax = axis information
    text_result = will be filled in with the alt_text and alt_html for the plot
    """

    

    sns.set(font_scale=1.5)
    bar_height = 0.2
    bar_width = [0]
    try:
        #aggregate/filter the data in the function so only one bar fails
        df = agg_fcn(df)
        
        if len(df.columns) > 1:
            raise ValueError("dataframe should have two columns (labels and values), found %s" % (df.columns))

        grouped_df = df.reset_index().set_axis(['label', 'value'], axis='columns')

        # TODO: Do we need this as a separate function?
        df_all_entries, df_only_small = process_trip_data(grouped_df.label.tolist(), grouped_df.value.tolist())

        # TODO: Fix this to be more pandas-like and change the "long" variable name
        for label in pd.unique(df_only_small['Label']):
            long = df_only_small[df_only_small['Label'] == label]
            # TODO: Remove if/else; if we only consider unique values, then long can never be empty
            if not long.empty:
                mode_prop = long['Proportion']
                mode_count = long['Value']
                vals_str = [f'{y:.1f} %\n({x:.0f})' if y > 4 else '' for x, y in zip(mode_count, mode_prop)]
                bar = ax.barh(y=bar_label, width=mode_prop, height=bar_height, left=bar_width, label=values_to_translations.get(label, label), color=colors[label])
                ax.bar_label(bar, label_type='center', labels=vals_str, rotation=90, fontsize=16)
                bar_width = [total + val for total, val in zip(bar_width, mode_prop)]
            else:
                print(f"{long} is empty")
        ax.tick_params(axis='y', labelsize=18)
        ax.tick_params(axis='x', labelsize=18, rotation=90)
        ncols = len(df_only_small)//5 if len(df_only_small) % 5 == 0 else len(df_only_small)//5 + 1
        
        ax.legend(bbox_to_anchor=(1, 1), loc='upper left', fancybox=True, shadow=True, fontsize=15, ncols=ncols)
            
        # Fix for the error: RuntimeError("Unknown return type"), adding the below line to address as mentioned here https://github.com/matplotlib/matplotlib/issues/25625/
        ax.set_xlim(right=ax.get_xlim()[1] + 1.0, auto=True)
        text_result[0], text_result[1] = store_alt_text_and_html_stacked_bar_chart(df_all_entries, bar_label, values_to_translations)
        print("After populating, %s" % text_result)
    except Exception as e:
        print(e)
        # tb.print_exception(type(e), e, e.__traceback__)
        #ax.set_title("Insufficient data", loc="center")
        ax.set_ylabel(bar_label)
        ax.yaxis.label.set(rotation='horizontal', ha='right', va='center', fontsize=18)
        ax.text(x = 0.5, y = 0.9, s = "Insufficient data", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, fontsize=20)
        # TODO: consider switching to a two column table
        ax.text(x = 0.5, y = 0.8, s = debug_df.to_string(), horizontalalignment='center', verticalalignment='top', transform=ax.transAxes, fontsize=10)
        text_result[0] = store_alt_text_missing(debug_df, None, bar_label)
        text_result[1] = store_alt_html_missing(debug_df, None, bar_label)
        # ax.yaxis.set_visible(False)

# Adds chart title, x and y axis label to the 100% Stacked Bar Chart
def set_title_and_save(fig, text_results, plot_title, file_name):
    # Setup label and title for the figure since these would be common for all sub-plots
    # We only need the axis to tweak the position (WHY!) so we do so by getting the first ax object
    ax = fig.get_axes()[-1]
    ax.set_xlabel('Proportion (Count)', fontsize=20)
    # fig.supylabel('Trip Types', fontsize=20, x=-0.12, y=0.5, rotation='vertical')
    fig.suptitle(plot_title, fontsize=25,va = 'bottom')
    plt.text(x=0, y=ax.xaxis.get_label().get_position()[0] - 0.62, s=f"Last updated {arrow.get()}", fontsize=12)
    plt.subplots_adjust(hspace=0.1, top= 0.95)

    # if nRows == 1, then plt.subplots returns a single axis object instead of an array
    # similarly we have text_result be a single list if nRows == 1 and a list of lists if nRows > 1
    # but then we want to wrap it so that it is a list of lists with a single top level element
    # so that the iteration logic below works
    if len(fig.get_axes()) == 1:
        text_results = [text_results]


    # The number of plots is not fixed. Let's iterate over the array that is passed in to handle the text results.
    # The number of axes in the figure is the number of plots
    concat_alt_text = plot_title
    concat_alt_html = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <p>{plot_title}</p>
    """
    for i in range(0, len(fig.get_axes())):
        concat_alt_text += text_results[i][0]
        concat_alt_html += f"<div style='float: left; padding-left: 20px, position: relative; width: 45%'>{text_results[i][1]}</div>"

    concat_alt_html += f"""
    </body>
    </html>
    """

    # Set up title and concatenate the text results
    # TODO: Consider using a dictionary or a data object instead of an array of arrays
    # for greater clarity
    alt_text = access_alt_text(concat_alt_text, file_name)
    alt_html = access_alt_html(concat_alt_html, file_name)
    fig.savefig(SAVE_DIR + file_name + ".png", bbox_inches='tight')
    plt.show()

def energy_impact(x,y,color,plot_title,file_name, values_to_translations={}):
    color = color.map({True: 'green', False: 'red'})
    objects = ('Energy Savings', 'Energy Loss')
    
    y_labels = y.map(lambda value: values_to_translations.get(value, value))
    plt.figure(figsize=(15, 8))
    width = 0.8
    ax = x.plot(kind='barh',width=width, color=color)
    ax.set_title(plot_title, fontsize=18)
    ax.set_xlabel('Energy_Impact(kWH)', fontsize=18)
    ax.set_ylabel('Replaced Mode',fontsize=18)
    ax.set_yticklabels(y_labels)
    ax.xaxis.set_tick_params(labelsize=15)
    ax.yaxis.set_tick_params(labelsize=15)
    ax.relim()
    ax.autoscale_view() 

    rects = ax.patches
    for rect in rects:
        x_value = rect.get_width()
        y_value = rect.get_y() + rect.get_height() / 2
        space = 5
        ha = 'left'
       
        if x_value < 0:
            space *= -1
            ha = 'right'
        
        label = "{:.1f}".format(x_value)

        # Create annotation
        plt.annotate(
            label,                      
            (x_value, y_value),         
            xytext=(space, 0),          
            textcoords="offset points", 
            va='center',                
            ha=ha, fontsize=12, color='black', fontweight='bold')
        
    # map names to colors
    cmap = {True: 'green', False: 'red'}  
    patches = [Patch(color=v, label=k) for k, v in cmap.items()]
    plt.text(0,-1.5,f"Last updated {arrow.get()}", fontsize=10)
    plt.legend(labels=objects, handles=patches, loc='upper right', borderaxespad=0, fontsize=15, frameon=True)
    plt.savefig(SAVE_DIR+file_name+".png", bbox_inches='tight')

def barplot_mode(data,x,y,x_label,plot_title, labels, file_name, values_to_translations={}):
    colours = dict(zip(labels, plt.cm.tab20.colors[:len(labels)]))
    sns.set(font_scale=1.5)
    f = plt.subplots(figsize=(15, 6))
    sns.set(style='whitegrid')
    ax = sns.barplot(x=x, y=y, palette=colours,data=data, ci=None)
    plt.xlabel(x_label, fontsize=23)
    plt.ylabel(y, fontsize=23)
    plt.title(plot_title, fontsize=25)

    if values_to_translations:
        x_ticks = ax.get_xticklabels()
        translated_labels = [values_to_translations.get(label.get_text(), label.get_text()) for label in x_ticks]
        ax.set_xticklabels(translated_labels)

    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')

    # y should be based on the max range + the biggest label ("Gas Car, with others")
    plt.text(0,-(data[y].max()/8 + 3.3),f"Last updated {arrow.get()}", fontsize=10)
    plt.savefig(SAVE_DIR+file_name+".png", bbox_inches='tight')

def barplot_mode2(data,x,y,y2,plot_title,file_name):
    all_labels= ['Gas Car, drove alone',
                 'Bus', 
                 'Train', 
                 'Free Shuttle',
                 'Taxi/Uber/Lyft', 
                 'Gas Car, with others', 
                 'Bikeshare',
                 'Scooter share',
                 'E-bike', 
                 'Walk', 
                 'Skate board', 
                 'Regular Bike', 
                 'Not a Trip',
                 'No Travel', 
                 'Same Mode', 
                 'E-car, drove alone',
                 'E-car, with others',
                 'Air',
                 'Other']
    
    colours = dict(zip(all_labels, plt.cm.tab20.colors[:len(all_labels)]))
    sns.set(font_scale=1.5)

    fig, ax1 = plt.subplots(figsize=(15,6))
    #bar plot creation
    ax1.set_title(plot_title, fontsize=16)
    plt.text(0,-2,f"Last updated {arrow.get()}", fontsize=10)
    ax1.set_xlabel(x, fontsize=16)
    ax1.set_ylabel(y, fontsize=16)
    ax1 = sns.barplot(x=x, y=y, data = data, palette=colours, ci=None)
    ax1.grid(False)
    
    #specify we want to share the same x-axis
    ax2 = ax1.twinx()
    color = 'tab:red'
    #line plot creation
    ax2.set_ylabel('Count', fontsize=16)
    ax2 = sns.pointplot(x=x, y=y2, data = data, sort=False, color=color)
    ax2.grid(False)
    plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
    plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
    plt.savefig(SAVE_DIR+file_name+".png", bbox_inches='tight')
    
def barplot_day(data,x,y,plot_title,file_name):
    sns.set(font_scale=1.5)
    f = plt.subplots(figsize=(15, 6))
    sns.set(style='whitegrid')
    ax = sns.barplot(x=x, y=y,data=data, ci=None, color='blue')
    plt.xlabel(x, fontsize=16)
    plt.ylabel(y, fontsize=16)
    plt.title(plot_title, fontsize=16)
    # heuristic where we take the max value and divide it by 8 to get the scale
    # the 8 is heuristic based on experimentation with the CanBikeCO data
    plt.text(0,-(data[y].max())/8,f"Last updated {arrow.get()}", fontsize=10)
    plt.savefig(SAVE_DIR+file_name+".png", bbox_inches='tight')

def CO2_impact(x,y,color,plot_title, xLabel, yLabel, file_name, values_to_translations={}):
    color = color.map({True: 'green', False: 'red'})
    objects = ('CO2 Reduction', 'CO2 Increase')

    y_labels = y.map(lambda value: values_to_translations.get(value, value))
    plt.figure(figsize=(15, 8))
    width = 0.8
    ax = x.plot(kind='barh',width=width, color=color)
    ax.set_title(plot_title, fontsize=18)
    ax.set_xlabel(xLabel, fontsize=18)
    ax.set_ylabel(yLabel,fontsize=18)
    ax.set_yticklabels(y_labels)
    ax.xaxis.set_tick_params(labelsize=15)
    ax.yaxis.set_tick_params(labelsize=15)
    ax.relim()
    ax.autoscale_view()

    rects = ax.patches
    for rect in rects:
        x_value = rect.get_width()
        y_value = rect.get_y() + rect.get_height() / 2
        space = 5
        ha = 'left'

        if x_value < 0:
            space *= -1
            ha = 'right'

        label = "{:.1f}".format(x_value)

        # Create annotation
        plt.annotate(
            label,
            (x_value, y_value),
            xytext=(space, 0),
            textcoords="offset points",
            va='center',
            ha=ha, fontsize=12, color='black', fontweight='bold')

    # map names to colors
    cmap = {True: 'green', False: 'red'}
    patches = [Patch(color=v, label=k) for k, v in cmap.items()]
    plt.text(0,-1.5,f"Last updated {arrow.get()}", fontsize=10)
    plt.legend(labels=objects, handles=patches, loc='upper right', borderaxespad=0, fontsize=15, frameon=True)
    plt.savefig(SAVE_DIR+file_name+".png", bbox_inches='tight')

def timeseries_plot(x,y,plot_title,ylab,file_name):
    fig, ax = plt.subplots(figsize=(16,4))
    sns.lineplot(ax=ax, x=x, y=y).set(title=plot_title, xlabel='Date', ylabel=ylab)
    plt.xticks(rotation=45)
    plt.subplots_adjust(bottom=0.25)
    ax.figure.savefig(SAVE_DIR+file_name+".png", bbox_inches='tight')

def timeseries_multi_plot(data,x,y,hue,plot_title,ylab,legend_title,file_name, values_to_translations={}):
    fig, ax = plt.subplots(figsize=(16,4))
    sns.lineplot(ax=ax, data=data, x=x, y=y, hue=hue).set(title=plot_title, xlabel='Date', ylabel=ylab)
    plt.xticks(rotation=45)
    plt.subplots_adjust(bottom=0.25)
    #  Get the current legend labels
    handles, labels = ax.get_legend_handles_labels()
    if values_to_translations:
        labels = [values_to_translations.get(label, label) for label in labels]
    ax.legend(handles,labels, bbox_to_anchor=[1.02, 1], loc='best', borderaxespad=0, title=legend_title)
    ax.figure.savefig(SAVE_DIR+file_name+".png", bbox_inches='tight')

def access_alt_text(alt_text, chart_name):
    """ Inputs:
    alt_text = the text describing the chart
    chart_name = the alt text file to save or update
    """
    f = open(SAVE_DIR+chart_name+".txt",'w')
    f.write(alt_text)
    f.close()
    return alt_text

def store_alt_text_generic(chart_description, chart_name, var_name):
    """ Inputs:
    chart_description = what type of chart is it
    chart_name = what to label chart by in the dictionary
    var_name = the variable being analyzed across the chart
    """
    # Fill out the alt text based on components of the chart and passed data
    alt_text = f"{chart_description} chart of {var_name}."
    alt_text = access_alt_text(alt_text, chart_name)
    return alt_text

def store_alt_text_bar(df, chart_name, var_name):
    """ Inputs:
    df = dataframe with index of item names, first column is counts
    chart_name = what to label chart by in the dictionary
    var_name = the variable being analyzed across pie slices
    """
    # Fill out the alt text based on components of the chart and passed data
    alt_text = f"Bar chart of {var_name}."
    for i in range(0,len(df)):
        alt_text += f" {df.index[i]} is {np.round(df.iloc[i,0], 1)}."
    alt_text = access_alt_text(alt_text, chart_name)
    return alt_text

def store_alt_text_timeseries(df, chart_name, var_name):
    """ Inputs:
    df = dataframe with first col of dates, second column is values
    chart_name = what to label chart by in the dictionary
    var_name = the variable being analyzed across pie slices
    """
    # Fill out the alt text based on components of the chart and passed data
    alt_text = f"Scatter chart of {var_name}."
    arg_min = np.argmin(df.iloc[:,1])
    arg_max = np.argmax(df.iloc[:,1])
    alt_text += f" First minimum is {np.round(df.iloc[arg_min,1], 1)} on {df.iloc[arg_min,0]}. First maximum is {np.round(df.iloc[arg_max,1], 1)} on {df.iloc[arg_max,0]}."
    alt_text = access_alt_text(alt_text, chart_name)
    return alt_text

# Creating html table with col as Trip Type, Label, Value, and Proportion
def access_alt_html(html_content, chart_name):
    """ Inputs:
    html_body = the text describing the chart
    chart_name = the alt text file to save or update
    var_name = the variable being analyzed across bars
    """
    with open(SAVE_DIR + chart_name + ".html", "w") as f:
        f.write(html_content)

    return html_content

# Appends bar information into into the alt_html
def store_alt_text_and_html_stacked_bar_chart(df, var_name, values_to_translations):
    """ Inputs:
    df = dataframe combining columns as Trip Type, Label, Value, Proportion
    chart_name = name of the chart
    """
    # Generate alt text file
    alt_text = f"\nStacked Bar of: {var_name}\n"
    for i in range(len(df)):
        alt_text += f"{values_to_translations.get(df['Label'].iloc[i], df['Label'].iloc[i])} is {df['Value'].iloc[i]}({df['Proportion'].iloc[i]}%).\n"

    # Generate html table
    alt_html = "\n"
    for i in range(len(df)):
        alt_html += f"<tr><td>{values_to_translations.get(df['Label'].iloc[i], df['Label'].iloc[i])}</td><td>{df['Value'].iloc[i]}</td><td>{df['Proportion'].iloc[i]}%</td></tr>"
    html_content = f"""
        <p>Trip Type: {var_name}</p>
        <table border="1" style="background-color: white;">
            <tr>
                <th>Label</th>
                <th>Value</th>
                <th>Proportion</th>
            </tr>
            {alt_html}
        </table>
    """
    return alt_text, html_content

def generate_missing_plot(plot_title,debug_df,file_name):
    f, ax = plt.subplots(figsize=(10,10))

    plt.title("Unable to generate plot\n"+plot_title+"\n Reason:", fontsize=25, color="red")
    # Must keep the patch visible; otherwise the entire figure becomes transparent
    # f.patch.set_visible(False)
    ax.axis('off')
    ax.axis('tight')
    # ax = sns.barplot(x=debug_df['count'],y=debug_df.index, palette=sns.color_palette("Reds",n_colors=10))
    # ax.set_xlim(0, None)
    # for i in ax.containers:
    #     ax.bar_label(i,)
    the_table = plt.table(cellText=debug_df.values,
              rowLabels=debug_df.index,
              colLabels=debug_df.columns,
              loc="center")
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(20)
    the_table.scale(1, 4)
    cellDict = the_table.get_celld()
    for i in range(1,len(debug_df)+1):
        currCellTextStr = cellDict[(i,0)].get_text().get_text()
        currCellTextFloat = float(currCellTextStr)
        if np.isnan(currCellTextFloat):
            cellDict[(i,0)].get_text().set_text("None")
        if np.isnan(currCellTextFloat) or currCellTextFloat == 0:
            cellDict[(i, 0)].get_text().set_color("red")
    plt.savefig(SAVE_DIR+file_name+".png", bbox_inches='tight')

def store_alt_text_missing(df, chart_name, var_name):
    """ Inputs:
    df = dataframe with index of debug information, first column is counts
    chart_name = what to label chart by in the dictionary
    var_name = the variable being analyzed across pie slices
    """
    # Fill out the alt text based on components of the chart and passed data
    alt_text = f"Unable to generate\nBar chart of {var_name}.\nReason:"
    for i in range(0,len(df)):
        alt_text += f" {df.index[i]} is {np.round(df.iloc[i,0], 1)}."

    # For the bar charts, there is no longer a 1:1 mapping between missing alt
    # text and a file. So we want to collect all the alt_text as strings and
    # then save it. We cannot just remove the call to `access_alt_text`, since
    # it will break other uses. So let's pass in None for the chart_name if we
    # don't want to save it.
    if chart_name is not None:
        alt_text = access_alt_text(alt_text, chart_name)
    return alt_text

def store_alt_html_missing(df, chart_name, var_name):
    """ Inputs:
    df = dataframe with index of debug information, first column is counts
    chart_name = what to label chart by in the dictionary
    var_name = the variable being analyzed across pie slices
    """
    # Fill out the alt text based on components of the chart and passed data
    alt_html = f"""
        <html>
        <body>
        <h2>Unable to generate\nBar chart of {var_name}. Reason:</h2>\n
    """
    alt_html += df.to_html()
    alt_html += f"""
        </body>
        </html>
    """
    if chart_name is not None:
        alt_html = access_alt_html(alt_html, chart_name)
    return alt_html
