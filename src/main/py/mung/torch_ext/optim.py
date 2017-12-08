import torch
from torch.optim.optimizer import Optimizer

# Modified Adagrad implementation from: 
# https://github.com/pytorch/pytorch/blob/master/torch/optim/adagrad.py
#
# Generic optimizer may also be useful
# https://github.com/pytorch/pytorch/blob/master/torch/optim/optimizer.py
class Adagrad(Optimizer):
    """Implements Adagrad algorithm.
    It has been proposed in `Adaptive Subgradient Methods for Online Learning
    and Stochastic Optimization`_.
    Arguments:
        params (iterable): iterable of parameters to optimize or dicts defining
            parameter groups
        lr (float, optional): learning rate (default: 1e-2)
        lr_decay (float, optional): learning rate decay (default: 0)
        weight_decay (float, optional): weight decay (L2 penalty) (default: 0)
    .. _Adaptive Subgradient Methods for Online Learning and Stochastic
        Optimization: http://jmlr.org/papers/v12/duchi11a.html
    """

    def __init__(self, params, lr=1e-2, lr_decay=0, weight_decay=0, l1_C=0, no_bias_l1=True, no_non_singleton_l1=True):
        defaults = dict(lr=lr, lr_decay=lr_decay, weight_decay=weight_decay, l1_C=l1_C)
        super(Adagrad, self).__init__(params, defaults)

        self._no_bias_l1 = no_bias_l1
        self._no_non_singleton_l1 = no_non_singleton_l1

        self.reset()

    def reset(self):
        for group in self.param_groups:
            for p in group['params']:
                state = self.state[p]
                state['step'] = 0
                state['sum'] = p.data.new().resize_as_(p.data).zero_()
                state['avg'] = p.data.new().resize_as_(p.data).zero_()
                state['zeros'] = torch.zeros(state['avg'].size())
                if p.is_cuda:
                    state['zeros'] = state['zeros'].cuda()

    def get_step(self):
        for group in self.param_groups:
            for p in group['params']:
                state = self.state[p]
                if 'step' in state:
                    return state['step']
        return None

    def share_memory(self):
        for group in self.param_groups:
            for p in group['params']:
                state = self.state[p]
                state['sum'].share_memory_()
                state['avg'].share_memory_()

    def step(self, closure=None):
        """Performs a single optimization step.
        Arguments:
            closure (callable, optional): A closure that reevaluates the model
                and returns the loss.
        """
        loss = None
        if closure is not None:
            loss = closure()
        for group in self.param_groups:
            for p in group['params']:
                if p.grad is None:
                    continue

                grad = p.grad.data
                state = self.state[p]

                state['step'] += 1

                if group['weight_decay'] != 0:
                    if p.grad.data.is_sparse:
                        raise RuntimeError("weight_decay option is not compatible with sparse gradients ")
                    grad = grad.add(group['weight_decay'], p.data)

                clr = group['lr'] / (1 + (state['step'] - 1) * group['lr_decay'])
                if group['l1_C'] != 0 and ((not self._no_bias_l1) or (len(p.data.size()) > 1 or p.data.size(0) > 1) and ((not self._no_non_singleton_l1) or p.data.size(0) == 1)): 
                    # FIXME Note this is a hack to not regularize biases and non-single unit layers
                    # l1 update.  See https://stanford.edu/~jduchi/projects/DuchiHaSi12_ismp.pdf
                    state['avg'].add_(1, grad)
                    state['sum'].addcmul_(1, grad, grad)
                    g_bar = state['avg'] / state['step']
                    adapt = state['sum'].sqrt().add(1e-10)
                    sparsity = torch.max(torch.abs(g_bar)-group['l1_C'], state['zeros'])
                    p.data = torch.sign(-g_bar)*(clr*state['step']/adapt)*sparsity
                elif p.grad.data.is_sparse:
                    grad = grad.coalesce()  # the update is non-linear so indices must be unique
                    grad_indices = grad._indices()
                    grad_values = grad._values()
                    size = torch.Size([x for x in grad.size()])

                    def make_sparse(values):
                        constructor = type(p.grad.data)
                        if grad_indices.dim() == 0 or values.dim() == 0:
                            return constructor()
                        return constructor(grad_indices, values, size)
                    state['sum'].add_(make_sparse(grad_values.pow(2)))
                    std = state['sum']._sparse_mask(grad)
                    std_values = std._values().sqrt_().add_(1e-10)
                    p.data.add_(-clr, make_sparse(grad_values / std_values))
                else:
                    state['sum'].addcmul_(1, grad, grad)
                    std = state['sum'].sqrt().add_(1e-10)
                    p.data.addcdiv_(-clr, grad, std)

        return loss
