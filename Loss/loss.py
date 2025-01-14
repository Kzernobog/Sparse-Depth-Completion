#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import torch
import torch.nn as nn
import torch.nn.functional as F
import pdb


def allowed_losses():
    return loss_dict.keys()


def define_loss(loss_name, *args):
    if loss_name not in allowed_losses():
        raise NotImplementedError('Loss functions {} is not yet implemented'.format(loss_name))
    else:
        return loss_dict[loss_name](*args)


class MAE_loss(nn.Module):
    def __init__(self, mask_intersec):
        super(MAE_loss, self).__init__()
        self.mask_intersec = mask_intersec

    def forward(self, prediction, gt, input, epoch=0):
        prediction = prediction[:, 0:1]
        abs_err = torch.abs(prediction - gt)
        mask = (gt > 0).detach()
        mae_loss = torch.mean(abs_err[mask])
        return mae_loss


class MAE_log_loss(nn.Module):
    def __init__(self):
        super(MAE_log_loss, self).__init__()

    def forward(self, prediction, gt):
        prediction = torch.clamp(prediction, min=0)
        abs_err = torch.abs(torch.log(prediction+1e-6) - torch.log(gt+1e-6))
        mask = (gt > 0).detach()
        mae_log_loss = torch.mean(abs_err[mask])
        return mae_log_loss


class MSE_loss(nn.Module):
    def __init__(self, mask_intersec):
        super(MSE_loss, self).__init__()
        self.weighted_mse = mask_intersec

    def forward(self, prediction, gt, weight_map, epoch=0):
        err = prediction[:,0:1] - gt
        mask = (gt > 0).detach()

        #use different weights over different bins in loss (distances divided in bins)
        if self.weighted_mse:
            weighted_mse_loss = 0
            max_val = torch.max(weight_map).int()
            for i in range(1, max_val + 1):
                weighted_mse_loss += torch.mean(err[weight_map == i]**2)
            return weighted_mse_loss / i
        mse_loss = torch.mean((err[mask])**2)
        return mse_loss


class MSE_loss_uncertainty(nn.Module):
    def __init__(self, mask_intersec):
        super(MSE_loss_uncertainty, self).__init__()
        self.mask_intersec = mask_intersec

    def forward(self, prediction, gt, weight_map, epoch=0):
        mask = (gt > 0).detach()
        depth = prediction[:, 0:1, :, :]
        conf = torch.abs(prediction[:, 1:, :, :])
        # conf = prediction[:, 1:, :, :]
        err = depth - gt
        conf_loss = torch.mean(0.5*(err[mask]**2)*torch.exp(-conf[mask]) + 0.5*conf[mask])
        # conf_loss = torch.mean(0.5*(err[mask]**2)*torch.exp(-conf[mask]) + 0.5*torch.log(torch.exp(conf[mask]) + 1))
        return conf_loss 


class MSE_log_loss(nn.Module):
    def __init__(self):
        super(MSE_log_loss, self).__init__()

    def forward(self, prediction, gt):
        prediction = torch.clamp(prediction, min=0)
        err = torch.log(prediction+1e-6) - torch.log(gt+1e-6)
        mask = (gt > 0).detach()
        mae_log_loss = torch.mean(err[mask]**2)
        return mae_log_loss


class Huber_loss(nn.Module):
    def __init__(self, mask_intersec, delta=10):
        super(Huber_loss, self).__init__()
        self.delta = delta
        self.mask_intersec = mask_intersec

    def forward(self, outputs, gt, input, epoch=0):
        outputs = outputs[:, 0:1, :, :]
        err = torch.abs(outputs - gt)
        mask = (gt > 0).detach()
#        if self.mask_intersec:
#            mask_input = (input>0).detach()
#            mask = (mask - mask_input)>0
        err = err[mask]
        squared_err = 0.5*err**2
        linear_err = err - 0.5*self.delta
        return torch.mean(torch.where(err < self.delta, squared_err, linear_err))



class Berhu_loss(nn.Module):
    def __init__(self, mask_intersec, delta=0.05):
        super(Berhu_loss, self).__init__()
        self.delta = delta
        self.mask_intersec = mask_intersec

    def forward(self, prediction, gt, weight_map, epoch=0):
        prediction = prediction[:, 0:1]
        err = torch.abs(prediction - gt)
        mask = (gt > 0).detach()
        err = torch.abs(err[mask])
        c = self.delta*err.max().item()
        squared_err = (err**2+c**2)/(2*c)
        linear_err = err
        return torch.mean(torch.where(err > c, squared_err, linear_err))


class Huber_delta1_loss(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, prediction, gt, input):
        mask = (gt > 0).detach().float()
        loss = F.smooth_l1_loss(prediction*mask, gt*mask, reduction='none')
        return torch.mean(loss)


class Disparity_Loss(nn.Module):
    def __init__(self, order=2):
        super(Disparity_Loss, self).__init__()
        self.order = order

    def forward(self, prediction, gt):
        mask = (gt > 0).detach()
        gt = gt[mask]
        gt = 1./gt
        prediction = prediction[mask]
        err = torch.abs(prediction - gt)
        err = torch.mean(err**self.order)
        return err


loss_dict = {
    'mse': MSE_loss,
    'mae': MAE_loss,
    'log_mse': MSE_log_loss,
    'log_mae': MAE_log_loss,
    'huber': Huber_loss,
    'huber1': Huber_delta1_loss,
    'berhu': Berhu_loss,
    'disp': Disparity_Loss,
    'uncert': MSE_loss_uncertainty}
