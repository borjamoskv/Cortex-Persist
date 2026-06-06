# MejoraloSessionRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Project** | **string** |  | 
**ScoreBefore** | **int32** |  | 
**ScoreAfter** | **int32** |  | 
**Actions** | Pointer to **[]string** |  | [optional] 

## Methods

### NewMejoraloSessionRequest

`func NewMejoraloSessionRequest(project string, scoreBefore int32, scoreAfter int32, ) *MejoraloSessionRequest`

NewMejoraloSessionRequest instantiates a new MejoraloSessionRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewMejoraloSessionRequestWithDefaults

`func NewMejoraloSessionRequestWithDefaults() *MejoraloSessionRequest`

NewMejoraloSessionRequestWithDefaults instantiates a new MejoraloSessionRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetProject

`func (o *MejoraloSessionRequest) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *MejoraloSessionRequest) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *MejoraloSessionRequest) SetProject(v string)`

SetProject sets Project field to given value.


### GetScoreBefore

`func (o *MejoraloSessionRequest) GetScoreBefore() int32`

GetScoreBefore returns the ScoreBefore field if non-nil, zero value otherwise.

### GetScoreBeforeOk

`func (o *MejoraloSessionRequest) GetScoreBeforeOk() (*int32, bool)`

GetScoreBeforeOk returns a tuple with the ScoreBefore field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetScoreBefore

`func (o *MejoraloSessionRequest) SetScoreBefore(v int32)`

SetScoreBefore sets ScoreBefore field to given value.


### GetScoreAfter

`func (o *MejoraloSessionRequest) GetScoreAfter() int32`

GetScoreAfter returns the ScoreAfter field if non-nil, zero value otherwise.

### GetScoreAfterOk

`func (o *MejoraloSessionRequest) GetScoreAfterOk() (*int32, bool)`

GetScoreAfterOk returns a tuple with the ScoreAfter field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetScoreAfter

`func (o *MejoraloSessionRequest) SetScoreAfter(v int32)`

SetScoreAfter sets ScoreAfter field to given value.


### GetActions

`func (o *MejoraloSessionRequest) GetActions() []string`

GetActions returns the Actions field if non-nil, zero value otherwise.

### GetActionsOk

`func (o *MejoraloSessionRequest) GetActionsOk() (*[]string, bool)`

GetActionsOk returns a tuple with the Actions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActions

`func (o *MejoraloSessionRequest) SetActions(v []string)`

SetActions sets Actions field to given value.

### HasActions

`func (o *MejoraloSessionRequest) HasActions() bool`

HasActions returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


