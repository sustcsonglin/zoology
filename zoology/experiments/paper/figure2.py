import uuid

import numpy as np

from zoology.config import DataConfig, LoggerConfig, ModelConfig, TrainConfig

sweep_id = uuid.uuid4().hex[:6]
sweep_name = "figure2" + sweep_id


VOCAB_SIZE = 8_192

configs = []
for input_seq_len, num_kv_pairs in [
    # (64, 4),
    # (128, 8),
    (512, 64),
    # (256, 16)
]:
    if input_seq_len == 1024:
        batch_size = 64
    elif input_seq_len == 512:
        batch_size = 128
    elif input_seq_len == 256:
        batch_size = 256
    else:
        batch_size = 512

    data = DataConfig(
        num_train_examples=100_000,
        num_test_examples=3_000,
        vocab_size=VOCAB_SIZE,
        input_seq_len=input_seq_len,
        batch_size=batch_size,
        # cache_dir="", # TODO: add a directory to cache your results!
        builder={
            "name": "zoology.data.associative_recall.multiquery_ar",
            "kwargs": {
                "num_kv_pairs": num_kv_pairs,
                "train_power_a": 0.01,
                "test_power_a": 0.01,
                "random_non_queries": False
            }
        }
    )

    for d_model in [
        # 64,
        # 128,
        # 256,
        # 128,
        # 64,
        # 128,
        # 256,
        # 512
        # 512
        64, 
        # 128,
        # 256,
        # 512
    ]:
        i = 0

        for lr in np.logspace(-4, -2, 4):
            i += 1
            if i != 3:
                continue
            MIXERS = {
                "attention": dict(
                    name="zoology.mixers.attention.MHA",
                    kwargs={
                        "dropout": 0.1,
                        "num_heads": 4
                    },
                ),
                "hyena": dict(
                    name="zoology.mixers.hyena.Hyena",
                    kwargs={
                        "l_max": input_seq_len
                    },
                ),
                "rwkv": dict(
                    name="zoology.mixers.rwkv.RWKVTimeMixer",
                    kwargs={
                        "l_max": input_seq_len,
                    },
                ),
                "base_conv": dict(
                    name="zoology.mixers.base_conv.BaseConv",
                    kwargs={
                        "l_max": input_seq_len,
                        # pass a list of kernel sizes for each of four layers
                        "kernel_size": [3, -1, 3, -1]
                    }
                ),
                "h3": dict(
                    name="zoology.mixers.h3.H3",
                    kwargs={
                        "l_max": input_seq_len,
                        "d_state": input_seq_len,  # makes it mathematically equivalent to Hyena
                        "head_dim": 2
                    }
                ),
                "based": dict(
                    name="zoology.mixers.hybrid.Hybrid",
                    kwargs={
                        "configs": [
                            dict(
                                name="zoology.mixers.base_conv.BaseConv",
                                kwargs={
                                    "l_max": input_seq_len,
                                    # pass a list of kernel sizes for each of four layers
                                    "kernel_size": 3,
                                    "implicit_long_conv": True,
                                }
                            ),
                            dict(
                                name="zoology.mixers.based.Based",
                                kwargs={
                                    "l_max": input_seq_len,
                                    "feature_dim": 8,
                                    "num_key_value_heads": 1,
                                    "num_heads": 1,
                                    "feature_name": "taylor_exp"
                                }
                            )
                        ]
                    }
                ),
                "mamba": dict(
                    name="zoology.mixers.mamba.Mamba",
                    kwargs={}
                ),
                "gla": dict(
                    name="fla.layers.gla.GatedLinearAttention",
                    kwargs={
                        "mode": "fused_recurrent",
                        "num_heads": 2,
                        'use_gk': True,
                        "use_gv": False,
                        "gate_logit_normalizer": 128,
                    }                   
                ),
                "hedgehog": dict(
                    name="fla.layers.linear_attn.LinearAttention",
                    kwargs={
                        "mode": "chunk",
                        "num_heads": 2,
                        # 'use_gk': True,
                        # "use_gv": False,
                        # "gate_logit_normalizer": 128,
                    }                   
                ),
                
                "abc": dict(
                    name="fla.layers.abc2.ABCAttention",
                    kwargs={
                        "num_heads": 1,
                        }                   
                ),

                "retnet": dict(
                    name="fla.layers.multiscale_retention.MultiScaleRetention",
                    kwargs={
                        "num_heads": 2,
                        "mode": "fused_recurrent"
                    }
                ),
            }
            for sequence_mixer in [
                'hedgehog',
                # "retnet"
            ]:

                if 'mamba' in sequence_mixer:
                    block_type = "MambaBlock"
                else:
                    block_type = "TransformerBlock"

                model = ModelConfig(
                    d_model=d_model,
                    n_layers=2 if sequence_mixer != "attention" else 2,
                    block_type=block_type,
                    max_position_embeddings=input_seq_len if sequence_mixer == "attention" else 0,
                    vocab_size=VOCAB_SIZE,
                    sequence_mixer=MIXERS[sequence_mixer],
                    state_mixer=dict(name="torch.nn.Identity", kwargs={})
                )
                config = TrainConfig(
                    model=model,
                    data=data,
                    learning_rate=lr,
                    max_epochs=64,
                    run_id=f"{sequence_mixer}-seqlen{input_seq_len}-dmodel{d_model}-lr{lr}-kv{num_kv_pairs}",
                    logger=LoggerConfig(
                        project_name="zoology",
                        entity="sonta"
                    )

                )
                configs.append(config)


