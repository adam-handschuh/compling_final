import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import spacy
import statistics as st
import math
from scipy.stats import mannwhitneyu

df = pd.read_excel("Corpus.xlsx")
nlp = spacy.load('en_core_web_sm')

def run_statistical_tests(labour, nui):
    print("\n=== Mann-Whitney U Test Results ===")

    metrics = {
        "MATTR": (labour.MATTR, nui.MATTR),
        "AWF": (labour.AWF, nui.AWF),
        "CTUR": (labour.CTUR, nui.CTUR),
        "MLT": (labour.MLT, nui.MLT)
    }

    for metric_name, (labour_data, nui_data) in metrics.items():
        u_stat, p_value = mannwhitneyu(labour_data, nui_data, alternative='two-sided')

        print(f"\nMetric: {metric_name}")
        print(f"  U statistic = {u_stat:.2f}")
        print(f"  p-value     = {p_value:.4f}")
        
        if p_value < 0.05:
            print("  → Significant difference between Labour and NUI panels.")
        else:
            print("  → No significant difference between Labour and NUI panels.")

class Panel:
    
    # Constructor
    def __init__(self, name):
        self.panel_name = name
        self.contributions = []
        # Metrics   (Lexical)
        self.MATTR = []       
        self.AWF = [] 
        # Metrics   (Structural)
        self.CTUR = [] 
        self.MLT = []

    
    # Functions
    def sentParser(self, contribution):
        doc = nlp(contribution)
        return [sent.text.strip() for sent in doc.sents]
    
    
    def getMATTR (self, text, window_size):
        words = text.split()
        if len(words) < window_size:
            return len(set(words)) / len(words) if words else 0

        ttrs = []
        for i in range(len(words) - window_size + 1):
            window = words[i:i + window_size]
            ttr = len(set(window)) / window_size
            ttrs.append(ttr)

        return sum(ttrs) / len(ttrs)
    
    def getAWF(self, text, freq_dict):
        words = text.lower().split()
        freqs = [math.log10(freq_dict.get(word, 1) + 1) for word in words]
        return sum(freqs) / len(freqs) if freqs else 0
    
    def getCTUR(self, text):
        subordinate_labels = {'advcl', 'csubj', 'ccomp', 'relcl', 'xcomp'}
        total_main_clauses = 0
        total_subordinate_clauses = 0
        doc = nlp(text)
        
        for sent in doc.sents:
            total_main_clauses += sum(1 for token in sent if token.dep_ == "ROOT")
            total_subordinate_clauses += sum(1 for token in sent if token.dep_ in subordinate_labels)

        if total_main_clauses == 0:
            return 0.0

        return (total_main_clauses + total_subordinate_clauses) / total_main_clauses

    def getMLT(self, text):
        doc = nlp(text)
        t_units = []

        for sent in doc.sents:
            # Split sentence into coordinated main clauses (T-units)
            clauses = [token for token in sent if token.dep_ == "ROOT"]
            if clauses:
                t_units.append(len(sent.text.split()))  # Word count per T-unit

        return np.mean(t_units) if t_units else 0


    def preprocess_text(self, text):
        # Replace newlines with a period and a space
        return text.replace('\n', '. ')
    
    def complexityAnalysis(self):
        counter = 0
        df = pd.read_csv("C:/Users/Adam/Desktop/College/Trinity/Year_4/Comp Ling/Final Task/all.txt", sep='\s+', header=None, names=["frequency", "word", "pos", "unknown"])
        bnc_freq_dict = dict(zip(df["word"], df["frequency"]))
        for contrib in self.contributions:
            contrib = self.preprocess_text(contrib)
            counter += 1
            print("\033[2J\033[H", end="")
            print(round(counter / len(self.contributions) * 100), "%")
            
            self.MATTR.append(self.getMATTR(contrib, 50))
            self.AWF.append(self.getAWF(contrib, bnc_freq_dict))
            self.CTUR.append(self.getCTUR(contrib))
            self.MLT.append(self.getMLT(contrib))
    
def exportGraph(panel):
    rows = ["MATTR", "AWF", "CTUR", "MTL"]
    columns = ["Minimum", "Maximum", "Median", "Mean", "Standard Deviation"]
    
    data = {
        "Minimum": [
            round(min(panel.MATTR), 3), 
            round(min(panel.AWF),3), 
            round(min(panel.CTUR), 3), 
            round(min(panel.MLT),3)
        ],
        "Maximum": [
            round(max(panel.MATTR), 3), 
            round(max(panel.AWF),3), 
            round(max(panel.CTUR), 3), 
            round(max(panel.MLT),3)
        ],
        "Median": [
            round(st.median(panel.MATTR), 3), 
            round(st.median(panel.AWF),3), 
            round(st.median(panel.CTUR), 3), 
            round(st.median(panel.MLT),3)
        ],
        "Mean": [
            round(st.mean(panel.MATTR), 3), 
            round(st.mean(panel.AWF),3), 
            round(st.mean(panel.CTUR), 3), 
            round(st.mean(panel.MLT),3)
        ],
        "Standard Deviation": [
            round(st.stdev(panel.MATTR), 3), 
            round(st.stdev(panel.AWF),3), 
            round(st.stdev(panel.CTUR), 3), 
            round(st.stdev(panel.MLT),3)
        ]
    }
    data_frame = pd.DataFrame(data,index=rows)
    fig, ax = plt.subplots(figsize=(8,3))
    ax.axis('off')
    ax.axis('tight')
    
    table = ax.table(cellText=data_frame.values,
                     rowLabels=data_frame.index,
                     colLabels=data_frame.columns,
                     cellLoc='center',
                     loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.2)

    plt.title(panel.panel_name, fontsize=14, pad=20)
    plt.tight_layout()
    plt.savefig(panel.panel_name + " complexity-breakdown.png", dpi=300)
    plt.close(fig)
    
if __name__ == '__main__':
    # 0. SETUP
    labour = Panel("Labour Panel Complexity Table")
    nui = Panel("NUI Complexity Table")
    
    # 1. DATA EXTRACTION
    for index, row in df.iterrows():
        panel_info = str(row.iloc[2]).strip().lower()
        text_info = row.iloc[9]

        if panel_info == "labour panel":
            labour.contributions.append(text_info)
        elif panel_info == "nui":
            nui.contributions.append(text_info)
    
    # 2. DATA PARSING
    labour.complexityAnalysis()
    nui.complexityAnalysis()
    
    # 3. DATA GRAPHING
    exportGraph(labour)
    exportGraph(nui)
    
    # 4. STATISTICAL TESTING
    run_statistical_tests(labour, nui)
