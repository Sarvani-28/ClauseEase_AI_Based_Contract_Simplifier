"""
Download and cache required Hugging Face models to avoid repeated downloads.
Run this script once on the machine (or from the Streamlit UI) to prefetch models.
"""

MODEL_NAMES = {
    "clause_detection": {
        "model": "nlpaueb/legal-bert-base-uncased",
        "type": "classification",
        "num_labels": 5
    },
    "simplifier": {
        "model": "tuner007/pegasus_paraphrase",
        "type": "seq2seq"
    }
}


def download_all_models():
    results = {}
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForSeq2SeqLM
    except Exception as e:
        return {"error": f"transformers not installed: {e}"}

    for key, cfg in MODEL_NAMES.items():
        model_name = cfg['model']
        results[key] = {"model": model_name}
        try:
            # download tokenizer
            AutoTokenizer.from_pretrained(model_name, local_files_only=False)
            results[key]['tokenizer'] = 'ok'
        except Exception as e:
            results[key]['tokenizer'] = f'error: {e}'
            continue

        try:
            if cfg['type'] == 'classification':
                AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=cfg.get('num_labels', 2))
            else:
                AutoModelForSeq2SeqLM.from_pretrained(model_name)
            results[key]['model_files'] = 'ok'
        except Exception as e:
            results[key]['model_files'] = f'error: {e}'

    return results


if __name__ == '__main__':
    print('Prefetching models... this may take several minutes and use several GB of disk.')
    res = download_all_models()
    print('Results:')
    for k, v in res.items():
        print(k, v)
