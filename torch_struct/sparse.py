import torch

def pad(x, v, dim, offset=0, semiring=None):
    "Symmetric zero padding"

    assert v % 2 == 0
    assert semiring is not None
    s = list(x.shape)
    offset = -offset
    orig =x.shape[dim]
    mag = abs(offset)
    s[dim] = v // 2 + mag
    p1 = torch.zeros(s, dtype=x.dtype, device=x.device)
    s[dim] = v // 2 + mag
    p2 = torch.zeros(s, dtype=x.dtype, device=x.device)
    if semiring:
        semiring.zero_(p1)
        semiring.zero_(p2)
    return torch.cat([p1, x, p2], dim=dim).narrow(dim, mag + offset, orig + v)

def pad_to(x, v, dim, semiring=None):
    cur = x.shape[dim]
    diff = (v - cur)
    return pad(x, diff, dim, semiring=semiring)

def sparse_to_dense(sparse, semiring=None, offset=0):
    assert semiring is not None
    n_size = sparse.shape[-2]
    off_size = sparse.shape[-1]
    p = off_size-1
    mag = abs(offset)
    y = torch.zeros(*sparse.shape[:-2], n_size + p +mag, n_size+mag,
                    dtype=sparse.dtype, device=sparse.device)
    if semiring is not None:
        semiring.zero_(y)
    r = y.unfold(-2, off_size, 1)
    r = r.diagonal(0, -3, -2).transpose(-1, -2)

    r[..., :n_size, :] = sparse[:]
    if offset > 0:
        a, b = 0, -offset
    elif offset < 0:
        a, b = 0, n_size + mag + offset
    elif offset == 0:
        a, b = 0, n_size + mag 
    ret = y[..., (off_size - 1) // 2 + offset : n_size + ((off_size +- 1) // 2) + offset  ,a : b]
    return ret
    
def dense_to_sparse(dense, band_size, semiring=None, offset=0):
    assert semiring is not None
    assert band_size % 2 == 1
    n_dim = -2
    off_dim = -1
    back = pad(dense, band_size-1, n_dim, offset, semiring=semiring).unfold(n_dim, band_size, 1)
    back = back.diagonal(0, off_dim-1, n_dim-1)
    return back.transpose(-2, -1)

def sparse_combine(y, x, fn = lambda a, b: (a*b).sum(-1), semiring=None):
    assert semiring is not None
    n_dim = -2
    off_dim = -1
    n = x.shape[n_dim]
    x_width = x.shape[-1]
    y_width = y.shape[-1]
    x = pad_to(x, n + x_width + y_width - 2, n_dim, semiring=semiring).unfold(n_dim, x_width + y_width - 1, 1)
    y = pad_to(y,  y_width + x_width + x_width -2, off_dim, semiring=semiring).unfold(off_dim, x_width, 1)
    x = x.transpose(-1, -2)
    return fn(x, y)

def get_banded(x, band):
    sparse = dense_to_sparse(x.transpose(-2, -1), band)
    o = sparse_to_dense(sparse)
    return o.transpose(-2, -1)

def sparse_banded_combine(x, y, b,
                          offset_x=0,
                          offset_y=0,
                          semiring=None,
                          fn= lambda a, b: (a*b).sum(-1)):
    "compute torch.matmul b1, b2"
    assert semiring is not None
    x = dense_to_sparse(x.transpose(-2, -1), b, offset=offset_x, semiring=semiring)
    y = dense_to_sparse(y, b, offset=offset_y, semiring=semiring)
    
    return sparse_to_dense(sparse_combine(y, x, fn=fn, semiring=semiring), semiring=semiring)
