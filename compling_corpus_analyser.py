import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import spacy
import statistics as st

df = pd.read_excel("Corpus.xlsx")
nlp = spacy.load('en_core_web_sm')

class Panel:
    
    # Constructor
    def __init__(self, name):
        self.panel_name = name
        self.contributions = []
        # Metrics   (Lexical)
        self.TTR = []                    # diversity
        self.word_length = []            # sophistication
        # Metrics   (Structural)
        self.complex_tunit_ratio = []    # complexity
        self.sentence_length = []        # extent


    
    # Functions
    def sentParser(self, contribution):
        doc = nlp(contribution)
        return [sent.text.strip() for sent in doc.sents]
    
    def getTTR (self, sent):
        words = sent.split()
        unique = []
        for word in words:
            if word not in unique:
                unique.append(word)
            
        return (len(unique) / len(words)) if words else 0
    
    def getWL(self, sent):
        word_lengths = []
        words = sent.split(' ')
        for word in words:
            if len(word) > 0:
                word_lengths.append(len(word))
            if len(word) > 17:
                print (word)
        return word_lengths
    
    def getCTUR(self, sents):
        subordinate_labels = {'advcl', 'csubj', 'ccomp', 'relcl', 'xcomp'}
        total_main_clauses = 0
        total_subordinate_clauses = 0
    
        for sent in sents:
            doc = nlp(sent)
        
            # Count main clauses by tokens labeled 'ROOT' (one for each independent clause).
            main_clauses = sum(1 for token in doc if token.dep_ == "ROOT")
        
            # Count subordinate clauses by tokens with labels often used for subordination.
            sub_clauses = sum(1 for token in doc if token.dep_ in subordinate_labels)
        
            total_main_clauses += main_clauses
            total_subordinate_clauses += sub_clauses
    
        # Avoid division by zero if no main clauses found.
        if total_main_clauses == 0:
            return 0.0
    
        ratio = (total_subordinate_clauses + total_main_clauses) / total_main_clauses
        return ratio

    def preprocess_text(self, text):
        # Replace newlines with a period and a space
        return text.replace('\n', '. ')
    
    def complexityAnalysis(self):
        counter = 0
        for contrib in self.contributions:
            contrib = self.preprocess_text(contrib)
            counter += 1
            # print("\033[2J\033[H", end="")
            # print(round(counter / len(self.contributions) * 100), "%")
            sentences = self.sentParser(contrib)
            # Debug print: show sentences with their lengths
            for sent in sentences:
                word_count = len(sent.split())
                if word_count < 110:
                    # Then process TTR, WL, etc.
                    ttr_val = self.getTTR(contrib)
                    self.TTR.append(ttr_val)
            
                    WL = self.getWL(sent)
                    self.word_length.extend(WL)
                    if(word_count > 0):
                        self.sentence_length.append(word_count) 
            
            # CTUR
            CTUR = self.getCTUR(self.sentParser(contrib))
            self.complex_tunit_ratio.append(CTUR)
    
def exportGraph(panel):
    rows = ["TTR", "WL", "CTUR", "SL"]
    columns = ["Minimum", "Maximum", "Median", "Mean", "Standard Deviation"]
    
    data = {
        "Minimum": [
            round(min(panel.TTR), 3), 
            min(panel.word_length), 
            round(min(panel.complex_tunit_ratio), 3), 
            min(panel.sentence_length)
        ],
        "Maximum": [
            round(max(panel.TTR), 3), 
            max(panel.word_length), 
            round(max(panel.complex_tunit_ratio), 3), 
            max(panel.sentence_length)
        ],
        "Median": [
            round(st.median(panel.TTR), 3), 
            st.median(panel.word_length), 
            round(st.median(panel.complex_tunit_ratio), 3), 
            st.median(panel.sentence_length)
        ],
        "Mean": [
            round(st.mean(panel.TTR), 3), 
            round(st.mean(panel.word_length),3), 
            round(st.mean(panel.complex_tunit_ratio), 3), 
            round(st.mean(panel.sentence_length),3)
        ],
        "Standard Deviation": [
            round(st.stdev(panel.TTR), 3), 
            round(st.stdev(panel.word_length),3), 
            round(st.stdev(panel.complex_tunit_ratio), 3), 
            round(st.stdev(panel.sentence_length),3)
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