# MissionResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**IntentId** | **int32** |  | 
**ResultId** | Pointer to **NullableInt32** |  | [optional] 
**Status** | **string** |  | 
**Stdout** | Pointer to **NullableString** |  | [optional] 
**Stderr** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewMissionResponse

`func NewMissionResponse(intentId int32, status string, ) *MissionResponse`

NewMissionResponse instantiates a new MissionResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewMissionResponseWithDefaults

`func NewMissionResponseWithDefaults() *MissionResponse`

NewMissionResponseWithDefaults instantiates a new MissionResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetIntentId

`func (o *MissionResponse) GetIntentId() int32`

GetIntentId returns the IntentId field if non-nil, zero value otherwise.

### GetIntentIdOk

`func (o *MissionResponse) GetIntentIdOk() (*int32, bool)`

GetIntentIdOk returns a tuple with the IntentId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIntentId

`func (o *MissionResponse) SetIntentId(v int32)`

SetIntentId sets IntentId field to given value.


### GetResultId

`func (o *MissionResponse) GetResultId() int32`

GetResultId returns the ResultId field if non-nil, zero value otherwise.

### GetResultIdOk

`func (o *MissionResponse) GetResultIdOk() (*int32, bool)`

GetResultIdOk returns a tuple with the ResultId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetResultId

`func (o *MissionResponse) SetResultId(v int32)`

SetResultId sets ResultId field to given value.

### HasResultId

`func (o *MissionResponse) HasResultId() bool`

HasResultId returns a boolean if a field has been set.

### SetResultIdNil

`func (o *MissionResponse) SetResultIdNil(b bool)`

 SetResultIdNil sets the value for ResultId to be an explicit nil

### UnsetResultId
`func (o *MissionResponse) UnsetResultId()`

UnsetResultId ensures that no value is present for ResultId, not even an explicit nil
### GetStatus

`func (o *MissionResponse) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *MissionResponse) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *MissionResponse) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetStdout

`func (o *MissionResponse) GetStdout() string`

GetStdout returns the Stdout field if non-nil, zero value otherwise.

### GetStdoutOk

`func (o *MissionResponse) GetStdoutOk() (*string, bool)`

GetStdoutOk returns a tuple with the Stdout field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStdout

`func (o *MissionResponse) SetStdout(v string)`

SetStdout sets Stdout field to given value.

### HasStdout

`func (o *MissionResponse) HasStdout() bool`

HasStdout returns a boolean if a field has been set.

### SetStdoutNil

`func (o *MissionResponse) SetStdoutNil(b bool)`

 SetStdoutNil sets the value for Stdout to be an explicit nil

### UnsetStdout
`func (o *MissionResponse) UnsetStdout()`

UnsetStdout ensures that no value is present for Stdout, not even an explicit nil
### GetStderr

`func (o *MissionResponse) GetStderr() string`

GetStderr returns the Stderr field if non-nil, zero value otherwise.

### GetStderrOk

`func (o *MissionResponse) GetStderrOk() (*string, bool)`

GetStderrOk returns a tuple with the Stderr field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStderr

`func (o *MissionResponse) SetStderr(v string)`

SetStderr sets Stderr field to given value.

### HasStderr

`func (o *MissionResponse) HasStderr() bool`

HasStderr returns a boolean if a field has been set.

### SetStderrNil

`func (o *MissionResponse) SetStderrNil(b bool)`

 SetStderrNil sets the value for Stderr to be an explicit nil

### UnsetStderr
`func (o *MissionResponse) UnsetStderr()`

UnsetStderr ensures that no value is present for Stderr, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


