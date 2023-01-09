# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from .postprocs import MultiStep
from .replay_buffers import (
    LazyMemmapStorage,
    LazyTensorStorage,
    ListStorage,
    PrioritizedReplayBuffer,
    RemoteTensorDictReplayBuffer,
    ReplayBuffer,
    Storage,
    TensorDictPrioritizedReplayBuffer,
    TensorDictReplayBuffer,
)
from .tensor_specs import (
    BinaryDiscreteTensorSpec,
    BoundedTensorSpec,
    CompositeSpec,
    CustomNdOneHotDiscreteTensorSpec,
    DEVICE_TYPING,
    DiscreteTensorSpec,
    MultiDiscreteTensorSpec,
    MultOneHotDiscreteTensorSpec,
    NdBoundedTensorSpec,
    NdOneHotDiscreteTensorSpec,
    NdUnboundedContinuousTensorSpec,
    NdUnboundedDiscreteTensorSpec,
    OneHotDiscreteTensorSpec,
    TensorSpec,
    UnboundedContinuousTensorSpec,
    UnboundedDiscreteTensorSpec,
)