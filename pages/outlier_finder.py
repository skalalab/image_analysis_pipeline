import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
import os
from dimension_reduction import dimension_reduction, create_figure
from navigation import render_top_menu
from features import get_features, fix_df

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
# Render the top menu 
render_top_menu()

col1, col2 = st.columns([0.4, 1])
with col1:
    st.title("Clustering")
    method = st.selectbox(
        "Select a clustering & outlier detection method",
        ["PCA: fitted features", "PCA: raw data", "UMAP: fitted features", "UMAP: raw data", "Image Level Boxplots"],
    )  
    upload_complete = False 
    if method == "Image Level Boxplots" or "fitted features" in method:
        uploaded_csv = st.file_uploader("Upload the CSV file from Region Props", type=["csv"])
    
        if uploaded_csv is not None:
        # Read the uploaded data
            df = pd.read_csv(uploaded_csv)
            numeric_cols, nadh_cols, fad_cols, morphology_cols, error_msg = get_features(df)
            if error_msg != "":
                st.markdown(f"<h5 style='text-align: center; color: red'>{error_msg}</h5>", unsafe_allow_html=True)
                upload_complete = False
            else:
                df = fix_df(df)
               # st.markdown("<h6 style='text-align: center;'>File uploaded successfully.</h6>", unsafe_allow_html=True)
                upload_complete = True
            if method == "Image Level Boxplots":
                # Define a callback function to reset other menus
                def reset_other_menus(selected_menu):
                    selected_value = st.session_state[selected_menu]
                    if selected_value != "Select":  # Only reset if the selection is not "Select"
                        for menu in ["menu_nadh", "menu_fad", "menu_morphology"]:
                            if menu != selected_menu:
                                st.session_state[menu] = "Select"
                        st.session_state.selected_menu = selected_menu

                # Render the dropdowns with callbacks
                selected_nadh = st.selectbox(
                    "Nadh Variables", 
                    ["Select"] + nadh_cols, 
                    index=0, 
                    key="menu_nadh",
                    on_change=reset_other_menus, 
                    args=("menu_nadh",)
                )

                selected_fad = st.selectbox(
                    "Fad Variables", 
                    ["Select"] + fad_cols, 
                    index=0, 
                    key="menu_fad",
                    on_change=reset_other_menus, 
                    args=("menu_fad",)
                )

                selected_morphology = st.selectbox(
                    "Morphology Variables", 
                    ["Select"] + morphology_cols, 
                    index=0, 
                    key="menu_morphology",
                    on_change=reset_other_menus, 
                    args=("menu_morphology",)
                )

                selected_var =  selected_nadh if selected_nadh != "Select" else selected_fad if selected_fad != "Select" else selected_morphology
            else:
                nadh_vars = st.multiselect(
                    "Select NADH Variables",
                    options= ["All NADH Variables"] + nadh_cols ,
                    default=[],
                    help="Select one or more columns corresponding to NADH variables."
                )
                fad_vars = st.multiselect(
                    "Select FAD Variables",
                    options= ["All FAD Variables"] + fad_cols,
                    default=[],
                    help="Select one or more columns corresponding to FAD variables."
                )
                morphology_vars = st.multiselect(
                    "Select Morphology Variables",
                    options= ["All Morphology Variables"] + morphology_cols ,
                    default=[],
                    help="Select one or more columns corresponding to morphology variables."
                )
        
    elif "raw data" in method:
        st.markdown("Instead of asking user to upload raw data files separately, **user can copy and paste the \
                 *path* of the folder containing the sdt files and masks in the text box below.**")
        
        st.markdown("<h5 style='text-align: center; color: red;'>Note: due to security concerns, this tool only works offline, as the online app does not have access to your local file system</h5>", unsafe_allow_html=True)
        
        folder_path = st.text_input("Enter a folder path:")

        if folder_path and st.button("List Files"):
            if os.path.isdir(folder_path):
                files = os.listdir(folder_path)
                st.write(f"Files in `{folder_path}`:")
                st.write(files)
                upload_complete = True
            else:
                st.markdown("***Warning: The provided path is not a directory or doesn't exist.***")

    if upload_complete is False:
        st.write("Please upload a file/folder path to begin.")


with col2:
    if upload_complete: 
        if "fitted features" in method: 
            if "All NADH Variables" in nadh_vars:
                nadh_vars = nadh_cols
            if "All FAD Variables" in fad_vars:
                fad_vars = fad_cols
            if "All Morphology Variables" in morphology_vars:
                morphology_vars = morphology_cols
            if len(nadh_vars + fad_vars + morphology_vars) > 1:
                selected_vars = nadh_vars + fad_vars + morphology_vars
                X = df[selected_vars]
                if "PCA" in method: 
                    df_reduced, exp_var  = dimension_reduction(X, n_components=2, method="PCA")
                    axis_labels = ["PC1", "PC2"]
                elif "UMAP" in method:
                    df_reduced, exp_var = dimension_reduction(X, n_components=2, method="UMAP")
                    axis_labels = ["UMAP1", "UMAP2"]
                else: 
                    st.write("Method not supported")
    
                st.markdown("<h5 style='text-align: center;'>Hover over to find the base_name of the outliers</h5>", unsafe_allow_html=True)
                # Add treatment and base_name back to the df_reduced for plotting/hovering
                df_reduced["base_name"] = df["base_name"]
                df_reduced["image_name"] = df["image_name"]
                df_reduced["treatment"] = df["treatment"]
                if "df_reduced" not in st.session_state:
                     st.session_state["df_reduced"] = df_reduced
                if "removed_images" not in st.session_state:
                    st.session_state["removed_images"] = []
                
                fig = create_figure(st.session_state["df_reduced"], axis_labels=axis_labels, exp_var=exp_var)

                clicked_points = plotly_events(
                    fig, 
                    click_event=True, 
                    hover_event=False, 
                    select_event=False
                )
                if clicked_points:
                    clicked_point = clicked_points[0]
                    point_index =  clicked_point["pointIndex"]
                    trace_index = clicked_point["curveNumber"]
                    clicked_image_name = fig.data[trace_index]['customdata'][point_index]
                    st.write(f"You clicked on image: {clicked_image_name}. Do you want to remove this image?")

                    if st.button("Confirm Removal"):
                        # Remove rows with the clicked base_name
                        st.session_state["df_reduced"] = st.session_state["df_reduced"][
                            st.session_state["df_reduced"]["image_name"] != clicked_image_name
                        ]
                        st.session_state["removed_images"].append(clicked_image_name)
                        st.rerun()

                if len(st.session_state["removed_images"]) > 0:
                    st.write("Removed images:")
                    st.write(st.session_state["removed_images"])
                    col1, col2 = st.columns([0.1, 1])
                    with col1:
                        if st.button("Reset"):
                            st.session_state["df_reduced"] = df_reduced
                            st.session_state["removed_images"] = []
                            st.rerun()
                    with col2:
                        df_outliers_removed = df[~df["image_name"].isin(st.session_state["removed_images"])]
                        st.download_button(
                            label="Download Outliers Removed CSV",
                            data=df_outliers_removed.to_csv(index=False),
                            file_name=f"{uploaded_csv.name}_outliers_removed.csv",
                            mime="text/csv"
                        )

                st.markdown("<h5 style='text-align: center;'>Click points to remove images where the outliers belong to</h5>", unsafe_allow_html=True)
            
            else:
                st.markdown("<h5 style='text-align: center;'>Please select at least two numeric variables for performing dimension reduction.</h5>", unsafe_allow_html=True)
        elif method == "Image Level Boxplots":
            if selected_var != "Select": 
                if (df["image_name"] == "missing image name").any():
                    st.markdown("<h5 style='text-align: center; color: Red;'>Warning: We cannot infer some/all image names from you base_name. We assume that the image name is the base_name without the cell number (which is found after the last underscore) </h5>", unsafe_allow_html=True)
                # Create a boxplot for the selected variable
                fig = px.box(df, x="image_name", y=selected_var, title=f"Boxplot for {selected_var}")
                st.plotly_chart(fig, use_container_width=True)
  
            else:
                st.markdown("<h5 style='text-align: center;'>Please select one variable to plot.</h5>", unsafe_allow_html=True)

        elif "raw data" in method:
            pass
    else:
        st.write("Waiting for file/folder path upload")