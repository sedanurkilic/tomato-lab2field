"""Shared lossless token-chunk SigLIP encoding for arbitrary text lists.

Usable for development v1 descriptions, development v2 overall_summary values,
and confirmation texts alike. No decoding/retokenization or token truncation.
The caller supplies a frozen eval text encoder and deterministic torch setup.
"""

ENCODING_RULE = 'lossless_token_chunks_l2_each_equal_mean_final_l2_v1'


def token_chunks(text, tokenizer, max_length=64):
    """Partition all content tokens once; budget model special tokens per chunk."""
    content_ids = tokenizer(text, add_special_tokens=False, truncation=False, verbose=False)['input_ids']
    budget = tokenizer.num_special_tokens_to_add(pair=False)
    capacity = max_length - budget
    if capacity <= 0:
        raise ValueError('Special-token budget leaves no content capacity')
    pieces = [content_ids[start:start+capacity] for start in range(0, len(content_ids), capacity)] or [[]]
    if [token for piece in pieces for token in piece] != content_ids:
        raise ValueError('Lossless content-token partition check failed')
    chunks = []
    for piece in pieces:
        # Work directly in token space: never decode a chunk into text.
        tokens = tokenizer.prepare_for_model(
            piece, add_special_tokens=True, padding='max_length',
            max_length=max_length, truncation=False, return_tensors='pt',
            return_attention_mask='attention_mask' in tokenizer.model_input_names,
        )
        # prepare_for_model receives one token list and may omit the batch axis.
        tokens = {name: value.unsqueeze(0) if value.ndim == 1 else value
                  for name, value in tokens.items()}
        expected_ids = tokenizer.build_inputs_with_special_tokens(piece)
        if len(expected_ids) != len(piece) + budget or len(expected_ids) > max_length:
            raise ValueError('Special-token budget/context check failed')
        if tokens['input_ids'].shape != (1, max_length):
            raise ValueError('Unexpected padded chunk shape')
        chunks.append(tokens)
    return chunks, {'content_token_count':len(content_ids), 'special_tokens_per_chunk':budget,
                    'content_capacity':capacity, 'chunk_count':len(pieces),
                    'chunk_content_token_counts':[len(piece) for piece in pieces],
                    'chunk_total_token_counts':[len(piece)+budget for piece in pieces],
                    'discarded_content_tokens':0, 'context_limit':max_length}


def encode_texts_lossless(texts, tokenizer, encoder):
    """L2 per chunk, equal mean, final L2; single chunks keep original result."""
    import torch
    if encoder.training or any(p.requires_grad for p in encoder.parameters()):
        raise ValueError('Encoder must be frozen and in eval mode')
    max_length=encoder.config.max_position_embeddings
    vectors, metadata = [], []
    device=next(encoder.parameters()).device
    with torch.inference_mode():
        for text in texts:
            chunks, info=token_chunks(text,tokenizer,max_length)
            embeddings=[]
            for tokens in chunks:
                tokens={name:value.to(device) for name,value in tokens.items()}
                vector=encoder(**tokens).pooler_output.squeeze(0)
                norm=vector.norm(p=2)
                if vector.shape!=(768,) or not torch.isfinite(vector).all() or not torch.isfinite(norm) or norm<=0:
                    raise ValueError('Invalid SigLIP chunk embedding')
                embeddings.append(vector/norm)
            if len(embeddings)==1:
                # Avoid a redundant normalization: exactly match the old path.
                pooled=embeddings[0]
            else:
                mean=torch.stack(embeddings).mean(dim=0)
                norm=mean.norm(p=2)
                if not torch.isfinite(norm) or norm<=0:
                    raise ValueError('Invalid pooled chunk norm')
                pooled=mean/norm
            vectors.append(pooled);metadata.append(info)
        if not vectors:
            raise ValueError('No texts to encode')
        result=torch.stack(vectors)
        if not torch.isfinite(result).all() or not torch.allclose(
                result.norm(dim=-1),torch.ones(len(vectors),device=device),atol=1e-6,rtol=0):
            raise ValueError('Final text embedding finite/unit-norm check failed')
    return result, metadata
