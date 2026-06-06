# \MissionsAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**LaunchMissionV1MissionsLaunchPost**](MissionsAPI.md#LaunchMissionV1MissionsLaunchPost) | **Post** /v1/missions/launch | Launch Mission
[**ListMissionsV1MissionsGet**](MissionsAPI.md#ListMissionsV1MissionsGet) | **Get** /v1/missions/ | List Missions



## LaunchMissionV1MissionsLaunchPost

> MissionResponse LaunchMissionV1MissionsLaunchPost(ctx).MissionLaunchRequest(missionLaunchRequest).Authorization(authorization).Execute()

Launch Mission



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {
	missionLaunchRequest := *openapiclient.NewMissionLaunchRequest("Project_example", "Goal_example") // MissionLaunchRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.MissionsAPI.LaunchMissionV1MissionsLaunchPost(context.Background()).MissionLaunchRequest(missionLaunchRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `MissionsAPI.LaunchMissionV1MissionsLaunchPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `LaunchMissionV1MissionsLaunchPost`: MissionResponse
	fmt.Fprintf(os.Stdout, "Response from `MissionsAPI.LaunchMissionV1MissionsLaunchPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiLaunchMissionV1MissionsLaunchPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **missionLaunchRequest** | [**MissionLaunchRequest**](MissionLaunchRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**MissionResponse**](MissionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListMissionsV1MissionsGet

> []map[string]interface{} ListMissionsV1MissionsGet(ctx).Project(project).Authorization(authorization).Execute()

List Missions



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {
	project := "project_example" // string |  (optional)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.MissionsAPI.ListMissionsV1MissionsGet(context.Background()).Project(project).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `MissionsAPI.ListMissionsV1MissionsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListMissionsV1MissionsGet`: []map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `MissionsAPI.ListMissionsV1MissionsGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListMissionsV1MissionsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **project** | **string** |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]map[string]interface{}**](map.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

