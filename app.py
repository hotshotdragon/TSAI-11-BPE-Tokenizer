import gradio as gr
import json
import pickle
from typing import List, Dict, Tuple, Union
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HindiTokenizer:
    """A tokenizer for Hindi text using BPE (Byte-Pair Encoding)."""
    
    def __init__(self, merges_path: Union[str, Path], vocab_path: Union[str, Path]):

        self.merges_path = Path(merges_path)
        self.vocab_path = Path(vocab_path)
        
        try:
            with open(self.merges_path, 'r', encoding='utf-8') as f:
                merges_json = json.load(f)
            self.merges = {tuple(map(int, k.split(','))): v for k, v in merges_json.items()}
            
            with open(self.vocab_path, 'rb') as f:
                self.vocab = pickle.load(f)
                
            logger.info(f"Loaded {len(self.merges)} merge rules and {len(self.vocab)} vocabulary items")
                
        except FileNotFoundError as e:
            logger.error(f"Required file not found: {e.filename}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in merges file: {self.merges_path}")
            raise
        except pickle.UnpicklingError:
            logger.error(f"Invalid pickle file: {self.vocab_path}")
            raise

    def get_stats(self, ids: List[int]) -> Dict[Tuple[int, int], int]:

        counts = {}
        for pair in zip(ids, ids[1:]):
            counts[pair] = counts.get(pair, 0) + 1
        return counts

    def merge(self, ids: List[int], pair: Tuple[int, int], idx: int) -> List[int]:

        newids = []
        i = 0
        while i < len(ids):
            if i < len(ids) - 1 and ids[i] == pair[0] and ids[i+1] == pair[1]:
                newids.append(idx)
                i += 2
            else:
                newids.append(ids[i])
                i += 1
        return newids

    def encode(self, text: str) -> List[int]:

        try:
            tokens = list(text.encode("utf-8"))
            while len(tokens) >= 2:
                stats = self.get_stats(tokens)
                pair = min(stats, key=lambda p: self.merges.get(p, float("inf")))
                if pair not in self.merges:
                    break
                idx = self.merges[pair]
                tokens = self.merge(tokens, pair, idx)
            return tokens
        except UnicodeEncodeError as e:
            logger.error(f"Invalid Unicode in input text: {e}")
            raise

    def decode(self, ids: List[int]) -> str:

        try:
            tokens = b"".join(self.vocab[idx] for idx in ids)
            return tokens.decode("utf-8", errors='replace')
        except KeyError as e:
            logger.error(f"Invalid token ID encountered: {e}")
            raise
        except UnicodeDecodeError as e:
            logger.error(f"Invalid UTF-8 bytes in decoded tokens: {e}")
            raise

def parse_token_ids(text: str) -> List[int]:
    try:
        if not text.strip():
            return []  # Return an empty list for empty input
        return [int(x.strip()) for x in text.split(',') if x.strip().isdigit()]
    except Exception as e:
        logger.error(f"Error parsing token IDs: {e}")
        raise ValueError("Token IDs must be comma-separated integers.")

def format_token_ids(ids: List[int]) -> str:
    """Format token IDs as a comma-separated string."""
    return ', '.join(map(str, ids))

def create_interface(tokenizer: HindiTokenizer) -> gr.Blocks:
    with gr.Blocks() as demo:
        gr.Markdown("""
        # Hindi Text Tokenizer
        
        This tool allows you to encode Hindi text into token IDs and decode token IDs back to Hindi text.
        
        **To encode:** Enter Hindi text in the first input box.  
        **To decode:** Enter comma-separated token IDs in the second input box.
        """)
        
        with gr.Row():
            with gr.Column():
                hindi_text = gr.Textbox(label="Input Hindi Text", placeholder="Enter Hindi text here...")
                encoded_output = gr.Textbox(label="Encoded Token IDs", interactive=False)
                encode_btn = gr.Button("Encode")
                
            with gr.Column():
                token_ids = gr.Textbox(label="Input Token IDs", placeholder="Enter comma-separated token IDs...")
                decoded_output = gr.Textbox(label="Decoded Hindi Text", interactive=False)
                decode_btn = gr.Button("Decode")
        
        encode_btn.click(fn=tokenizer.encode, inputs=hindi_text, outputs=encoded_output)
        decode_btn.click(fn=lambda x: tokenizer.decode(parse_token_ids(x)), inputs=token_ids, outputs=decoded_output)
        
        gr.Examples(
            examples=[
                ["हरि तुम हरो जन की भीर।","280, 925, 676, 331, 1123, 409, 542, 298, 273"],
                ["नैना निपट बंकट छबि अटके।", "272, 1292, 420, 886, 321, 306, 838, 321, 623, 307, 266, 2146, 273"]
            ],
            inputs=[hindi_text, token_ids]
        )
    
    return demo

def main():
    tokenizer = HindiTokenizer(
        merges_path="tsai_hindi_bpe_tokens.json",
        vocab_path="tsai_hindi_vocab.pkl"
    )
    demo = create_interface(tokenizer)
    demo.launch(share=True)

if __name__ == "__main__":
    main()