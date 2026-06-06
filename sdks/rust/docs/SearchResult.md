# SearchResult

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**fact_id** | **i32** |  | 
**project** | **String** |  | 
**content** | **String** |  | 
**fact_type** | **String** |  | 
**score** | **f64** |  | 
**tags** | **Vec<String>** |  | 
**created_at** | **String** |  | 
**updated_at** | **String** |  | 
**meta** | Option<**std::collections::HashMap<String, serde_json::Value>**> |  | [optional]
**hash** | Option<**String**> |  | [optional]
**context** | Option<**std::collections::HashMap<String, serde_json::Value>**> | Graph-RAG context (subgraph or related entities) | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


