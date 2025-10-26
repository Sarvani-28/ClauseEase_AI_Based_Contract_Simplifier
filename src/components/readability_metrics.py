"""Text readability metrics calculation"""

from nltk.tokenize import sent_tokenize, word_tokenize
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO
from collections import Counter

def count_syllables(word):
    """Count syllables in word"""
    word = word.lower()
    syllables = 0
    vowels = "aeiouy"
    
    if len(word) <= 1:
        return 1
    
    if word.endswith('e'):
        word = word[:-1]
    
    previous_was_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not previous_was_vowel:
            syllables += 1
        previous_was_vowel = is_vowel
    
    return max(1, syllables)

def count_complex_words(text):
    """Count 3+ syllable words"""
    words = word_tokenize(text.lower())
    complex_words = [w for w in words if len(w) > 2 and count_syllables(w) >= 3]
    return len(complex_words)

def calculate_all_metrics(text):
    """Calculate text statistics"""
    if not text or len(text.strip()) == 0:
        return {
            "sentence_count": 0,
            "word_count": 0,
            "avg_words_per_sentence": 0,
            "complex_word_count": 0
        }
    
    try:
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        words = [w for w in words if w.isalpha()]
        
        return {
            "sentence_count": len(sentences),
            "word_count": len(words),
            "avg_words_per_sentence": round(len(words) / len(sentences), 2) if len(sentences) > 0 else 0,
            "complex_word_count": count_complex_words(text)
        }
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        return {
            "sentence_count": 0,
            "word_count": 0,
            "avg_words_per_sentence": 0,
            "complex_word_count": 0
        }


def generate_clause_type_chart(clause_type_summary):
    """Generate clause pie chart"""
    try:
        if not clause_type_summary or len(clause_type_summary) == 0:
            clause_type_summary = {'General': 100}
        
        labels = list(clause_type_summary.keys())
        sizes = list(clause_type_summary.values())
        
        # Chart colors
        colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', 
            '#EC4899', '#0EA5E9', '#FB923C', '#22C55E'
        ]
        
        fig = plt.figure(figsize=(8, 6))
        
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, 
                colors=colors[:len(labels)], textprops={'fontsize': 11, 'weight': 'bold'})
        plt.title('Clause Types Distribution', fontsize=14, weight='bold', pad=20)
        plt.axis('equal')
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=80, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        
        return f"data:image/png;base64,{image_base64}"
    except Exception as e:
        print(f"Error generating clause type chart: {e}")
        return None


def generate_stats_chart(original_metrics, simplified_metrics):
    """Generate comparison bar chart"""
    try:
        categories = ['Word Count', 'Sentence Count', 'Avg Words/Sentence', 'Complex Words']
        
        # Extract original values
        original_values = [
            original_metrics.get('word_count', 0),
            original_metrics.get('sentence_count', 0),
            original_metrics.get('avg_words_per_sentence', 0),
            original_metrics.get('complex_word_count', 0)
        ]
        
        # Extract simplified values
        simplified_values = [
            simplified_metrics.get('word_count', 0),
            simplified_metrics.get('sentence_count', 0),
            simplified_metrics.get('avg_words_per_sentence', 0),
            simplified_metrics.get('complex_word_count', 0)
        ]
        
        x = range(len(categories))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create side-by-side bars
        bars1 = ax.bar([i - width/2 for i in x], original_values, width, 
                        label='Original', color='#2563EB', edgecolor='#1E40AF', linewidth=1.5)
        bars2 = ax.bar([i + width/2 for i in x], simplified_values, width, 
                        label='Simplified', color='#A855F7', edgecolor='#7C3AED', linewidth=1.5)
        
        # Style chart
        ax.set_xlabel('Metrics', fontsize=12, weight='bold')
        ax.set_ylabel('Values', fontsize=12, weight='bold')
        ax.set_title('Text Statistics Comparison', fontsize=14, weight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontsize=10)
        ax.legend(fontsize=11, loc='upper right')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=80, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        
        return f"data:image/png;base64,{image_base64}"
    except Exception as e:
        print(f"Error generating stats chart: {e}")
        return None
