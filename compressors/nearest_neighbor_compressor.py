import torch
import numpy as np
from scipy import stats
from utils.vecs_io import fvecs_read
from utils.vec_np import normalize


class NearestNeighborCompressor(object):
    def __init__(self, size, shape, c_dim=32, k=64):
        self.size = size
        self.shape = shape
        self.dim = c_dim if c_dim < size else size
        self.K = k
        if self.K == self.dim:
            self.codewords = stats.ortho_group.rvs(self.dim).astype(np.float32)
        else:
            _, self.codewords = normalize(fvecs_read(
                './codebook/angular_dim_{}_Ks_{}.fvecs'.format(self.dim, self.K)))
        self.c_dagger = np.linalg.pinv(self.codewords.T)

        self.codewords = torch.from_numpy(self.codewords).cuda()
        self.c_dagger = torch.from_numpy(self.c_dagger).cuda()
        self.code_dtype = torch.uint8 if self.K <= 2 ** 8 else torch.int32

    def compress(self, vec):

        vec = vec.view(-1, self.dim)

        # calculate probability, complexity: O(d*K)
        p = torch.mm(self.c_dagger, vec.transpose(0, 1)).transpose(0, 1)
        probability = torch.abs(p)

        # choose codeword
        codes = torch.argmax(probability, dim=1)

        u = p.gather(dim=1, index=codes.view(-1, 1)).view(-1)
        return [u, codes.type(self.code_dtype)]

    def decompress(self, signature):
        [norms, codes] = signature
        codes = codes.view(-1).type(torch.long)
        norms = norms.view(-1)
        vec = self.codewords[codes]
        recover = torch.mul(vec, norms.view(-1, 1).expand_as(vec))
        return recover.view(self.shape)

