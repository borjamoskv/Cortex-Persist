# \MissionsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**launch_mission_v1_missions_launch_post**](MissionsApi.md#launch_mission_v1_missions_launch_post) | **POST** /v1/missions/launch | Launch Mission
[**list_missions_v1_missions_get**](MissionsApi.md#list_missions_v1_missions_get) | **GET** /v1/missions/ | List Missions



## launch_mission_v1_missions_launch_post

> models::MissionResponse launch_mission_v1_missions_launch_post(mission_launch_request, authorization)
Launch Mission

Launch a new swarm mission through the CORTEX Launchpad.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**mission_launch_request** | [**MissionLaunchRequest**](MissionLaunchRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::MissionResponse**](MissionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## list_missions_v1_missions_get

> Vec<std::collections::HashMap<String, serde_json::Value>> list_missions_v1_missions_get(project, authorization)
List Missions

List recent mission intents and reports from the ledger.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**project** | Option<**String**> |  |  |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<std::collections::HashMap<String, serde_json::Value>>**](std::collections::HashMap.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

