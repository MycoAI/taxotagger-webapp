import os
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st
from taxotagger import ProjectConfig, TaxoTagger
from taxotagger.defaults import PRETRAINED_MODELS, TAXONOMY_LEVELS
from taxotagger.utils import parse_fasta, parse_unite_fasta_header

# Global variables
LOGO_IMAGE = "images/TaxoTagger-logo.svg"

# Config page
st.set_page_config(
    page_title="TaxoTagger DNA Barcode Identification",
    page_icon=LOGO_IMAGE,
    layout="centered",
)

# Title
col1, col2 = st.columns([1, 6], vertical_alignment="bottom")
with col1:
    st.image(LOGO_IMAGE, width=90)
with col2:
    st.title("Taxonomy Tagger")
    st.markdown("*Taxonomy identification, powered by AI and Semantic Search*")


# Initialize TaxoTagger
@st.cache_resource
def initialize_taxotagger():
    """Initialize the TaxoTagger object."""
    config = ProjectConfig()
    return TaxoTagger(config)


tt = initialize_taxotagger()


# Input method selection
def validate_input(fasta_content):
    """Validate the FASTA input."""
    try:
        header_seq_dict = parse_fasta(fasta_content)
    except ValueError as e:
        st.error(
            e.args[0] + "\n\nPlease ensure all FASTA headers are unique.", icon="⚠️"
        )
        st.stop()

    seq_ids = []
    for header in header_seq_dict:
        seq_id = parse_unite_fasta_header(header)[0]
        if seq_id not in seq_ids:
            seq_ids.append(seq_id)
        else:
            st.error(
                f"Duplicate sequence ID found: `{seq_id}`\n\nPlease ensure all sequence IDs are unique.",
                icon="⚠️",
            )
            st.stop()

    num_seqs = len(header_seq_dict)
    num_valid_headers = 0
    for header in header_seq_dict:
        if len(header) > 1:
            num_valid_headers += 1

    if num_valid_headers != num_seqs:
        st.error(
            "Invalid FASTA header(s) found. Please ensure that each header starts with '>' plus at least one more non-empty character.",
            icon="⚠️",
        )
        st.stop()

    if num_seqs > 100:
        st.error("Please limit the number of sequences to 100 or fewer.", icon="⚠️")
        st.stop()
    else:
        st.markdown(
            f"<p style='font-size: smaller; color: gray;'>You provided {num_seqs} valid sequences (max: 100)</p>",
            unsafe_allow_html=True,
        )

    st.session_state["seq_ids"] = seq_ids
    st.session_state["fasta_content"] = fasta_content


st.subheader("Enter DNA Sequence")
input_method = st.radio(
    "Choose input method:",
    ["Upload FASTA file(s)", "Enter FASTA text"],
    horizontal=True,
    label_visibility="collapsed",
    on_change=st.session_state.clear,
)

if input_method == "Enter FASTA text":
    fasta_content = st.text_area(
        "Enter FASTA sequence(s):",
        height=200,
        placeholder=">seq1\nATGC...\n>seq2\nCGTA...",
    )
    if fasta_content:
        validate_input(fasta_content)
    else:
        st.session_state.clear()

else:
    uploaded_files = st.file_uploader(
        "Upload FASTA files (max 100 sequences total)",
        type=["fasta", "fas", "fa"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        fasta_content = ""
        for uploaded_file in uploaded_files:
            # "/n" is needed to ensure the last sequence is not concatenated with the next one
            file_content = uploaded_file.getvalue().decode() + "\n"
            fasta_content += file_content
        validate_input(fasta_content)
    else:
        st.session_state.clear()

# Configure settings
st.subheader("Settings")

## Embedding model selection
model_options = PRETRAINED_MODELS.keys()
col1, col2 = st.columns([2, 1])
with col1:
    st.write("Select embedding model:")
with col2:
    st.session_state["selected_model"] = st.selectbox(
        "Select embedding model", model_options, label_visibility="collapsed"
    )

## Number of top matched results to display
col1, col2 = st.columns([2, 1])
with col1:
    st.write("Number of top matched results to display:")
with col2:
    st.session_state["top_n"] = st.number_input(
        label="Number of top matched results to display",
        min_value=1,
        max_value=5,
        value=2,
        step=1,
        format="%d",
        label_visibility="collapsed",
    )


# Function to process FASTA input and run TaxoTagger
def process_fasta_and_run(fasta_content):
    """Process the FASTA content and run TaxoTagger."""
    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, suffix=".fasta"
    ) as temp_fasta:
        temp_fasta.write(fasta_content)
        temp_fasta.flush()

        try:
            results = tt.search(
                temp_fasta.name,
                model_id=st.session_state["selected_model"],
                limit=st.session_state["top_n"],
            )
            return results
        finally:
            os.unlink(temp_fasta.name)


# Run button
if st.button("Run TaxoTagger", type="primary", use_container_width=True):
    if "fasta_content" not in st.session_state:
        st.error("Please provide FASTA input before running the analysis.", icon="💡")
        st.stop()

    results = process_fasta_and_run(st.session_state["fasta_content"])
    seq_ids = st.session_state["seq_ids"]

    # Check if the number of results matches the number of input sequences
    if len(results[TAXONOMY_LEVELS[0]]) != len(seq_ids):
        st.error(
            f"Mismatch between number of input sequences ({len(seq_ids)}) and results ({len(results[TAXONOMY_LEVELS[0]])}). Some sequences may not have been processed.",
            icon="⚠️",
        )
        # Identify unprocessed sequences
        processed_ids = set()
        for level in TAXONOMY_LEVELS:
            for result_list in results[level]:
                for result in result_list:
                    if "id" in result:
                        processed_ids.add(result["id"])
        unprocessed_ids = set(seq_ids) - processed_ids
        if unprocessed_ids:
            st.warning("The following sequences were not processed:")
            for unprocessed_id in unprocessed_ids:
                st.write(f"- {unprocessed_id}")

    # Process results
    results_by_seq = {}
    for i, seq_id in enumerate(seq_ids):
        results_by_seq[seq_id] = []
        for j in range(st.session_state["top_n"]):
            result = {}
            result["Sequence_ID"] = seq_id
            result["Rank"] = j + 1
            for level in TAXONOMY_LEVELS:
                level_cap = level.capitalize()
                try:
                    match = results[level][i][j]
                    value = match["entity"].get(level, "")
                    if value:
                        result[level_cap] = value
                        result[level_cap + "_Hit"] = match["id"]
                        result[level_cap + "_Similarity"] = match["distance"]
                    else:
                        result[level_cap] = ""
                        result[level_cap + "_Hit"] = ""
                        result[level_cap + "_Similarity"] = ""
                except IndexError:
                    # Handle the case where there are fewer results than expected
                    result[level_cap] = "No match found"
            results_by_seq[seq_id].append(result)
    st.session_state["results_by_seq"] = results_by_seq

if "results_by_seq" in st.session_state:
    results_by_seq = st.session_state["results_by_seq"]

    # Display results for the selected sequence
    st.subheader(
        "Results",
        help="""The predicted taxonomy labels for each input DNA sequence are displayed below
            with a format of 'TaxonomyLabel (ID;COS)' in each cell. Where, 'ID' is the ID of the
            matched DNA sequence, and 'COS' is the cosine similarity between the input DNA sequence
            and the matched DNA sequence, ranging from 0 (no match) to 1 (perfect match).""",
    )
    selected_seq_id = st.selectbox(
        "For input sequence:",
        results_by_seq.keys(),
    )

    df = pd.DataFrame(results_by_seq[selected_seq_id])
    df = df.drop(columns=["Sequence_ID"])  # Drop the sequence ID column
    df.set_index("Rank", inplace=True)  # Set the rank as the index
    for level in TAXONOMY_LEVELS:  # combine taxonomy label with the hit and similarity
        level_cap = level.capitalize()
        df[level_cap] = (
            df[level_cap]
            + " ("
            + df[level_cap + "_Hit"]
            + ";"
            + df[level_cap + "_Similarity"].round(3).astype(str)
            + ")"
        )
        df = df.drop(columns=[level_cap + "_Hit", level_cap + "_Similarity"])
    st.dataframe(df)

    # Combine results of all sequences for download
    combined_results = []
    for seq_id in results_by_seq:
        combined_results.extend(results_by_seq[seq_id])
    combined_df = pd.DataFrame(combined_results)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    file_name = f"taxotagger_results_{timestamp}.csv"
    st.download_button(
        label="Download all results",
        data=combined_df.to_csv(index=False),
        file_name=file_name,
        mime="text/csv",
    )


# Footer
st.markdown(
    "<div style='text-align: center; width: 100%; position: fixed; bottom: 40px; left: 0;'><a href='https://github.com/MycoAI/taxotagger' target='_blank'><img src='https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png' alt='GitHub Logo' style='width: 40px; height: 40px; opacity: 0.5;'></a></div>",
    unsafe_allow_html=True,
)

st.markdown(
    "<div style='text-align: center; width: 100%; position: fixed; bottom: 0; left: 0;'><p style='font-size: smaller; color: gray;'>@ 2024 <a href='https://www.esciencecenter.nl/' style='color: gray; text-decoration: underline; text-decoration-color: rgba(128, 128, 128, 0.5);'>Netherlands eScience Center</a></p></div>",
    unsafe_allow_html=True,
)
