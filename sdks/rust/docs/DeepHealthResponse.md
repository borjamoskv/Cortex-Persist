# DeepHealthResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **String** |  | 
**version** | **String** |  | 
**schema_version** | **String** |  | 
**checks** | [**std::collections::HashMap<String, models::HealthCheckDetail>**](HealthCheckDetail.md) |  | 
**latency_ms** | **f64** |  | 
**p95_latency_ms** | Option<**f64**> | p95 latency of ambient context boot | [optional]
**stale_ratio** | Option<**f64**> | Ratio of facts older than 180 days with no hits | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


