# FactResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **i32** |  | 
**project** | **String** |  | 
**content** | **String** |  | 
**fact_type** | **String** |  | 
**tags** | **Vec<String>** |  | 
**created_at** | **String** |  | 
**updated_at** | **String** |  | 
**confidence** | Option<[**models::Confidence**](Confidence.md)> |  | [optional]
**valid_from** | Option<**String**> |  | [optional]
**valid_until** | Option<**String**> |  | [optional]
**source** | Option<**String**> |  | [optional]
**meta** | Option<**std::collections::HashMap<String, serde_json::Value>**> |  | [optional]
**is_tombstoned** | Option<**bool**> |  | [optional][default to false]
**hash** | Option<**String**> |  | [optional]
**tx_id** | Option<**String**> |  | [optional]
**consensus_score** | Option<**f64**> |  | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


