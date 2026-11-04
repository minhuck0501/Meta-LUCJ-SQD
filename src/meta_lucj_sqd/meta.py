from dataclasses import dataclass

import numpy as np


@dataclass
class AffineModel:
    center: float
    scale: float
    coefficients: np.ndarray

    def predict(self,distance):
        return np.array([1.,(distance-self.center)/self.scale])@self.coefficients


def fit_affine(distances,features,ridge):
    distances=np.asarray(distances,dtype=float)
    features=np.asarray(features,dtype=float)
    if distances.ndim!=1 or features.ndim!=2 or len(distances)!=len(features) or len(distances)<2:
        raise ValueError('Invalid training arrays')
    center=float(distances.mean());scale=float(distances.std())
    if scale<=0 or ridge<0 or not np.all(np.isfinite(features)):
        raise ValueError('Invalid training scale or regularization')
    design=np.column_stack([np.ones(len(distances)),(distances-center)/scale])
    penalty=np.diag([0.,ridge])
    coefficients=np.linalg.solve(design.T@design+penalty,design.T@features)
    return AffineModel(center,scale,coefficients)
