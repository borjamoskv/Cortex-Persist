# JobRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**TaskType** | **string** |  | 
**Payload** | **map[string]interface{}** |  | 
**Sla** | [**JobSLA**](JobSLA.md) |  | 

## Methods

### NewJobRequest

`func NewJobRequest(taskType string, payload map[string]interface{}, sla JobSLA, ) *JobRequest`

NewJobRequest instantiates a new JobRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewJobRequestWithDefaults

`func NewJobRequestWithDefaults() *JobRequest`

NewJobRequestWithDefaults instantiates a new JobRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetTaskType

`func (o *JobRequest) GetTaskType() string`

GetTaskType returns the TaskType field if non-nil, zero value otherwise.

### GetTaskTypeOk

`func (o *JobRequest) GetTaskTypeOk() (*string, bool)`

GetTaskTypeOk returns a tuple with the TaskType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTaskType

`func (o *JobRequest) SetTaskType(v string)`

SetTaskType sets TaskType field to given value.


### GetPayload

`func (o *JobRequest) GetPayload() map[string]interface{}`

GetPayload returns the Payload field if non-nil, zero value otherwise.

### GetPayloadOk

`func (o *JobRequest) GetPayloadOk() (*map[string]interface{}, bool)`

GetPayloadOk returns a tuple with the Payload field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPayload

`func (o *JobRequest) SetPayload(v map[string]interface{})`

SetPayload sets Payload field to given value.


### GetSla

`func (o *JobRequest) GetSla() JobSLA`

GetSla returns the Sla field if non-nil, zero value otherwise.

### GetSlaOk

`func (o *JobRequest) GetSlaOk() (*JobSLA, bool)`

GetSlaOk returns a tuple with the Sla field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSla

`func (o *JobRequest) SetSla(v JobSLA)`

SetSla sets Sla field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


