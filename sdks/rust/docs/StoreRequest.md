# StoreRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**project** | **String** | Project/namespace for the fact | 
**content** | **String** | The fact content | 
**fact_type** | Option<**String**> | Type: knowledge, decision, mistake, bridge, ghost | [optional][default to knowledge]
**tags** | Option<**Vec<String>**> | Optional tags | [optional]
**source** | Option<**String**> | Origin of the fact (e.g. agent:vex) | [optional][default to ]
**confidence** | Option<**String**> | Optional confidence level (C1-C5) | [optional]
**meta** | Option<**std::collections::HashMap<String, serde_json::Value>**> | Graph-RAG context (subgraph or related entities) | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


