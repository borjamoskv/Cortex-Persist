# CheckpointResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**CheckpointId** | [**NullableCheckpointId**](CheckpointId.md) |  | 
**Message** | **string** |  | 
**Status** | Pointer to **string** |  | [optional] [default to "success"]

## Methods

### NewCheckpointResponse

`func NewCheckpointResponse(checkpointId NullableCheckpointId, message string, ) *CheckpointResponse`

NewCheckpointResponse instantiates a new CheckpointResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewCheckpointResponseWithDefaults

`func NewCheckpointResponseWithDefaults() *CheckpointResponse`

NewCheckpointResponseWithDefaults instantiates a new CheckpointResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetCheckpointId

`func (o *CheckpointResponse) GetCheckpointId() CheckpointId`

GetCheckpointId returns the CheckpointId field if non-nil, zero value otherwise.

### GetCheckpointIdOk

`func (o *CheckpointResponse) GetCheckpointIdOk() (*CheckpointId, bool)`

GetCheckpointIdOk returns a tuple with the CheckpointId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCheckpointId

`func (o *CheckpointResponse) SetCheckpointId(v CheckpointId)`

SetCheckpointId sets CheckpointId field to given value.


### SetCheckpointIdNil

`func (o *CheckpointResponse) SetCheckpointIdNil(b bool)`

 SetCheckpointIdNil sets the value for CheckpointId to be an explicit nil

### UnsetCheckpointId
`func (o *CheckpointResponse) UnsetCheckpointId()`

UnsetCheckpointId ensures that no value is present for CheckpointId, not even an explicit nil
### GetMessage

`func (o *CheckpointResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *CheckpointResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *CheckpointResponse) SetMessage(v string)`

SetMessage sets Message field to given value.


### GetStatus

`func (o *CheckpointResponse) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *CheckpointResponse) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *CheckpointResponse) SetStatus(v string)`

SetStatus sets Status field to given value.

### HasStatus

`func (o *CheckpointResponse) HasStatus() bool`

HasStatus returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


