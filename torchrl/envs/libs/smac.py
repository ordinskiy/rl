from typing import Dict, Optional

import torch
from tensordict.tensordict import TensorDict, TensorDictBase

from torchrl.data import (
    CompositeSpec,
    CustomNdOneHotDiscreteTensorSpec,
    NdUnboundedContinuousTensorSpec,
    TensorSpec,
    UnboundedContinuousTensorSpec,
)
from torchrl.envs import GymLikeEnv

try:
    import smac
    import smac.env
    from smac.env.starcraft2.maps import smac_maps

    _has_smac = True
except ImportError as err:
    _has_smac = False
    IMPORT_ERR = str(err)


def _get_envs():
    if not _has_smac:
        return []
    return [map_name for map_name, _ in smac_maps.get_smac_map_registry().items()]


class SC2Wrapper(GymLikeEnv):
    """SMAC (StarCraft Multi-Agent Challenge) environment wrapper.

    Examples:
        >>> env = smac.env.StarCraft2Env("8m", seed=42) # Seed cannot be changed once environment was created.
        >>> env = SC2Wrapper(env)
        >>> td = env.reset()
        >>> td["action"] = env.action_spec.rand()
        >>> td = env.step(td)
        >>> print(td)
        TensorDict(
            fields={
                action: Tensor(torch.Size([8, 14]), dtype=torch.int64),
                done: Tensor(torch.Size([1]), dtype=torch.bool),
                next: TensorDict(
                    fields={
                        observation: Tensor(torch.Size([8, 80]), dtype=torch.float32)},
                    batch_size=torch.Size([]),
                    device=cpu,
                    is_shared=False),
                observation: Tensor(torch.Size([8, 80]), dtype=torch.float32),
                reward: Tensor(torch.Size([1]), dtype=torch.float32)},
            batch_size=torch.Size([]),
            device=cpu,
            is_shared=False)
        >>> print(env.available_envs)
        ['3m', '8m', '25m', '5m_vs_6m', '8m_vs_9m', ...]
    """

    git_url = "https://github.com/oxwhirl/smac"
    available_envs = _get_envs()
    libname = "smac"

    def __init__(self, env: smac.env.StarCraft2Env = None, **kwargs):
        if env is not None:
            kwargs["env"] = env
        super().__init__(**kwargs)

    def _check_kwargs(self, kwargs: Dict):
        if "env" not in kwargs:
            raise TypeError("Could not find environment key 'env' in kwargs.")
        env = kwargs["env"]
        if not isinstance(env, (smac.env.StarCraft2Env,)):
            raise TypeError("env is not of type 'smac.env.StarCraft2Env'.")

    def _build_env(self, env, **kwargs) -> smac.env.StarCraft2Env:
        # StarCraft2Env must be initialized before _make_specs.
        env.reset()
        return env

    def _make_specs(self, env: smac.env.StarCraft2Env) -> None:
        # Extract specs from definition.
        self.reward_spec = self._make_reward_spec()

        # Extract specs from instance.
        # To extract these specs environment must be fully initialized with env.reset().
        self.input_spec = self._make_input_spec(env)
        self.observation_spec = self._make_observation_spec(env)

        # TODO: add support for the state.
        # self.state_spec = self._make_state_spec(env)
        # self.input_spec["state"] = self._state_spec
        # self._state_example = self._make_state_example(env)

    def _init_env(self) -> None:
        pass

    def _make_reward_spec(self) -> TensorSpec:
        return UnboundedContinuousTensorSpec(device=self.device)

    def _make_input_spec(self, env: smac.env.StarCraft2Env) -> TensorSpec:
        action_spec = CustomNdOneHotDiscreteTensorSpec(
            torch.tensor(env.get_avail_actions(), dtype=torch.bool), device=self.device
        )
        return CompositeSpec(action=action_spec)

    def _make_observation_spec(self, env: smac.env.StarCraft2Env) -> TensorSpec:
        info = env.get_env_info()
        size = torch.Size((info["n_agents"], info["obs_shape"]))
        obs_spec = NdUnboundedContinuousTensorSpec(size, device=self.device)
        return CompositeSpec(observation=obs_spec)

    def _set_seed(self, seed: Optional[int]):
        raise NotImplementedError(
            "Seed cannot be changed once environment was created."
        )

    def _reset(
        self, tensordict: Optional[TensorDictBase] = None, **kwargs
    ) -> TensorDictBase:
        env: smac.env.StarCraft2Env = self._env
        obs, state = env.reset()

        # collect outputs
        # TODO: add support for the state.
        # state_dict = self.read_state(state)
        obs_dict = self.read_obs(obs)
        done = torch.zeros(self.batch_size, dtype=torch.bool)

        self._is_done = done

        # build results
        tensordict_out = TensorDict(
            source=obs_dict,
            batch_size=self.batch_size,
            device=self.device,
        )
        tensordict_out.set("done", done)
        # TODO: add support for the state.
        # tensordict_out["state"] = state_dict
        # TODO: return available actions?

        return tensordict_out

    def _action_transform(self, action):
        action_np = self.action_spec.to_numpy(action)
        return action_np

    def _step(self, tensordict: TensorDictBase) -> TensorDictBase:
        env: smac.env.StarCraft2Env = self._env

        # perform actions
        action = tensordict.get("action")  # this is a list of actions for each agent
        action_np = self._action_transform(action)

        # Actions are validated by the environment.
        reward, done, info = env.step(action_np)

        # collect outputs
        # state_dict = self.read_state(state)
        obs_dict = self.read_obs(env.get_obs())
        reward = self._to_tensor(reward, dtype=self.reward_spec.dtype)
        done = self._to_tensor(done, dtype=torch.bool)

        # build results
        tensordict_out = TensorDict(
            source=obs_dict,
            batch_size=tensordict.batch_size,
            device=self.device,
        )
        tensordict_out.set("reward", reward)
        tensordict_out.set("done", done)
        # TODO: support state.
        # tensordict_out["state"] = state_dict

        # Update available actions mask.
        self.input_spec = self._make_input_spec(env)

        return tensordict_out

    def get_seed(self) -> Optional[int]:
        return self._env.seed()


class SC2Env(SC2Wrapper):
    """SMAC (StarCraft Multi-Agent Challenge) environment wrapper.

    Examples:
        >>> env = SC2Env(map_name="8m", seed=42)
        >>> td = env.rand_step()
        >>> print(td)
        TensorDict(
            fields={
                action: Tensor(torch.Size([8, 14]), dtype=torch.int64),
                done: Tensor(torch.Size([1]), dtype=torch.bool),
                next: TensorDict(
                    fields={
                        observation: Tensor(torch.Size([8, 80]), dtype=torch.float32)},
                    batch_size=torch.Size([]),
                    device=cpu,
                    is_shared=False),
                reward: Tensor(torch.Size([1]), dtype=torch.float32)},
            batch_size=torch.Size([]),
            device=cpu,
            is_shared=False)
        >>> print(env.available_envs)
        ['3m', '8m', '25m', '5m_vs_6m', '8m_vs_9m', ...]
    """

    def __init__(self, map_name: str, seed: Optional[int] = None, **kwargs):
        kwargs["map_name"] = map_name
        if seed is not None:
            kwargs["seed"] = seed
        super().__init__(**kwargs)

    def _check_kwargs(self, kwargs: Dict):
        if "map_name" not in kwargs:
            raise TypeError("Expected 'map_name' to be part of kwargs")

    def _build_env(
        self,
        map_name: str,
        seed: Optional[int] = None,
        **kwargs,
    ) -> smac.env.StarCraft2Env:
        if not _has_smac:
            raise RuntimeError(
                f"smac not found, unable to create smac.env.StarCraft2Env. "
                f"Consider installing smac. More info:"
                f" {self.git_url}. (Original error message during import: {IMPORT_ERR})."
            )

        self.wrapper_frame_skip = 1
        env = smac.env.StarCraft2Env(map_name, seed=seed, **kwargs)

        return super()._build_env(env)