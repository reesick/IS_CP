"""Published mathematical objectives; these kernels alone are not defenses.

CaD arXiv2610.35566v1 Eq13; MIRAGE arXiv2606.26199v2 global/local
cosine and secant equations. Callers must supply the real model representations.
"""

def reference_attention_objective(queries,keys,reference_start,reference_end,attention_mask=None,query_chunk=128):
    """CaD ascent objective on normalized/rotary-applied target queries.

    Q: B,H,target_queries,D; K: B,H,all_keys,D. Reference indices are in
    the model's ACTUAL joint key sequence. Never substitute arbitrary features.
    Additive masks follow the model; boolean masks use True=allowed.
    Chunking changes storage layout, not the per-head/per-query objective.
    """
    import torch
    if queries.ndim!=4 or keys.ndim!=4 or queries.shape[:2]!=keys.shape[:2] or queries.shape[-1]!=keys.shape[-1]:
        raise ValueError('Expected compatible B,H,N,D query/key tensors.')
    if not 0<=reference_start<reference_end<=keys.shape[-2] or query_chunk<1:
        raise ValueError('Invalid reference range or query chunk.')
    terms=[]
    for start in range(0,queries.shape[-2],query_chunk):
        q=queries[:,:,start:start+query_chunk].float()
        scores=q@keys.float().transpose(-1,-2)/(queries.shape[-1]**.5)
        if attention_mask is not None:
            mask=attention_mask
            if mask.ndim>=2 and mask.shape[-2]==queries.shape[-2]:
                mask=mask[...,start:start+query_chunk,:]
            scores=scores.masked_fill(~mask,-torch.inf) if mask.dtype==torch.bool else scores+mask
        # logsumexp ratio equals summing ordinary softmax over reference keys.
        mass=(torch.logsumexp(scores[...,reference_start:reference_end],dim=-1)-torch.logsumexp(scores,dim=-1)).exp()
        if not torch.isfinite(mass).all():
            raise ValueError('Attention contains queries with no allowed key.')
        terms.append((1-mass).square().reshape(-1))
    return -torch.cat(terms).mean()

def target_cosines(features,targets):
    import torch.nn.functional as F
    if features.ndim!=2 or targets.ndim!=2 or features.shape[-1]!=targets.shape[-1] or targets.shape[0]==0:
        raise ValueError('Expected nonempty matching embedding matrices.')
    return (F.normalize(features,dim=-1)@F.normalize(targets,dim=-1).T).mean(dim=-1)

def global_local_objective(global_features,local_features,targets,local_weight=.25,top_k=8):
    global_scores=target_cosines(global_features,targets)
    local_scores=target_cosines(local_features,targets)
    if not 1<=top_k<=local_scores.numel():
        raise ValueError('Invalid top-k patch count.')
    return global_scores.mean()+local_weight*local_scores.topk(top_k).values.mean()

def secant_gradient(g1,g2,d1,d2,current):
    """Published scalar-secant prediction; zero displacement keeps latest grad."""
    import torch
    s=d1-d2
    denominator=(s*s).sum()
    if denominator<=torch.finfo(s.dtype).eps:
        return g1.clone()
    return g1+(g1-g2)*(s*(current-d1)).sum()/denominator

def project_rgb(candidate,original,epsilon):
    import torch
    if not 0<epsilon<=1:
        raise ValueError('RGB epsilon must be in (0,1].')
    return torch.maximum(torch.minimum(candidate,original+epsilon),original-epsilon).clamp(0,1)
