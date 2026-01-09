"""
Stage-4 Behavioral Phase Inference

This package implements HMM-based behavioral phase inference
from Stage-3 cognitive observations.
"""

from .hmm_model import GaussianHMM, HMMParameters
from .state_store import PerUserStateStore, UserState
from .inference import PhaseInference
from .consumer import Stage4Consumer, ConsumerConfig
from .producer import PhaseProducer, ProducerConfig

__all__ = [
    'GaussianHMM',
    'HMMParameters', 
    'PerUserStateStore',
    'UserState',
    'PhaseInference',
    'Stage4Consumer',
    'ConsumerConfig',
    'PhaseProducer',
    'ProducerConfig'
]
