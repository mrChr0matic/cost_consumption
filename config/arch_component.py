ARCH_COMPONENT_MAP = {
        "Generative AI": {
            "Databricks Mosaic AI": {
                "Claude Sonnet": ["4.5", "4.0", "3.7"],
                "Claude Opus": ["4.5", "4.1", "4.0"],
                "LLaMA": ["4", "3.3", "3.1"],
                "Mistral": ["Large", "Medium", "Small"],
                "GPT OSS": ["120B", "20B", "7B"],
                "Gemma": ["3-12B", "2-9B", "2-2B"]
            },
            "AWS Bedrock": {
                "Claude": ["Sonnet 4.5", "Opus 4.5", "Sonnet 4.0"],
                "LLaMA": ["3", "2", "1"],
                "Mistral": ["Large", "Medium", "Small"],
                "Amazon Titan": ["Text Express", "Text G1", "Text Lite"]


            },
            "AWS SageMaker": {
                 "LLaMA": ["3", "2", "1"],
                 "Mistral": ["Large", "Medium", "Small"],
                 "SageMaker JumpStart": ["NeoX", "J", "Lite"]
            },

            "Azure AI Foundry": {
                  "GPT": ["4.1", "4o", "4 Turbo"],
                  "LLaMA": ["3", "2", "1"],
                   "Mistral": ["Large", "Medium", "Small"],
                   "Phi": ["3", "2", "1"]
            }
            },
        "RAG (Retrieval Augmented Generation)": {
            "Databricks Mosaic AI": {
                    "Claude Sonnet": ["4.5", "4.0", "3.7"],
                     "LLaMA": ["3.1", "3.0", "2"],
                    "Mistral": ["Large", "Medium", "Small"]
            },
            "AWS Bedrock": {
                    "Claude": ["Sonnet 4.5", "Sonnet 4.0", "Opus 4.1"],
                    "Mistral": ["Large", "Medium", "Small"],
                    "Amazon Titan": ["Embeddings G1", "Embeddings Lite", "Embeddings v2"]
            },
            "AWS SageMaker": {
                    "LLaMA": ["3", "2", "1"],
                    "Mistral": ["Large", "Medium", "Small"],
                    "FAISS": ["GPU", "CPU", "Distributed"]
            },
            "Azure AI Foundry": {
                    "GPT": ["4o", "4.1", "4 Turbo"],
                    "Mistral": ["Large", "Medium", "Small"],
                    "Cohere": ["Embed v3", "Embed v2", "Embed v1"]
            }
            },
        "Fine-tuning": {
            "Databricks Mosaic AI": {
                    "LLaMA": ["3.3", "3.1", "3.0"],
                    "Mistral": ["Large", "Medium", "Small"],
                    "Gemma": ["3-12B", "2-9B", "2-2B"]
            },
            "AWS Bedrock": {
                     "Claude": ["Sonnet", "Opus", "Instant"],
                     "LLaMA": ["3", "2", "1"]
            },
             "AWS SageMaker": {
                     "LLaMA": ["3", "2", "1"],
                     "Mistral": ["Large", "Medium", "Small"],
                     "Cohere": ["Command R+", "Command R", "Command"]
            },
            "Azure AI Foundry": {
                    "GPT": ["3.5 Turbo", "3.5", "3"],
                    "LLaMA": ["3", "2", "1"],
                     "Mistral": ["Large", "Medium", "Small"]
            }
             },
        "Embeddings / Vector Search": {
            "Databricks Mosaic AI": {
                    "BGE": ["Large", "Base", "Small"],
                    "GTE": ["Large", "Base", "Small"]
             },
            "AWS Bedrock": {
                     "Amazon Titan": ["Embedding G1", "Embedding Lite", "Embedding v2"],
                    "Cohere": ["Embed v3", "Embed v2", "Embed v1"]
            },
            "AWS SageMaker": {
                    "FAISS": ["GPU", "CPU", "Distributed"],
                    "OpenSearch": ["Vector", "Hybrid", "Dense"]
            },
            "Azure AI Foundry": {
                     "text-embedding": ["3-large", "3-small", "ada-002"]
                
            }
            }
            }
