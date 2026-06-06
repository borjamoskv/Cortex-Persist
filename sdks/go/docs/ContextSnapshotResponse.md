# ContextSnapshotResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ActiveProject** | Pointer to **NullableString** |  | [optional] 
**Confidence** | **string** |  | 
**SignalsUsed** | **int32** |  | 
**Summary** | **string** |  | 
**TopSignals** | Pointer to [**[]ContextSignalModel**](ContextSignalModel.md) |  | [optional] 
**ProjectsRanked** | Pointer to [**[]ProjectScoreModel**](ProjectScoreModel.md) |  | [optional] 

## Methods

### NewContextSnapshotResponse

`func NewContextSnapshotResponse(confidence string, signalsUsed int32, summary string, ) *ContextSnapshotResponse`

NewContextSnapshotResponse instantiates a new ContextSnapshotResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewContextSnapshotResponseWithDefaults

`func NewContextSnapshotResponseWithDefaults() *ContextSnapshotResponse`

NewContextSnapshotResponseWithDefaults instantiates a new ContextSnapshotResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetActiveProject

`func (o *ContextSnapshotResponse) GetActiveProject() string`

GetActiveProject returns the ActiveProject field if non-nil, zero value otherwise.

### GetActiveProjectOk

`func (o *ContextSnapshotResponse) GetActiveProjectOk() (*string, bool)`

GetActiveProjectOk returns a tuple with the ActiveProject field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActiveProject

`func (o *ContextSnapshotResponse) SetActiveProject(v string)`

SetActiveProject sets ActiveProject field to given value.

### HasActiveProject

`func (o *ContextSnapshotResponse) HasActiveProject() bool`

HasActiveProject returns a boolean if a field has been set.

### SetActiveProjectNil

`func (o *ContextSnapshotResponse) SetActiveProjectNil(b bool)`

 SetActiveProjectNil sets the value for ActiveProject to be an explicit nil

### UnsetActiveProject
`func (o *ContextSnapshotResponse) UnsetActiveProject()`

UnsetActiveProject ensures that no value is present for ActiveProject, not even an explicit nil
### GetConfidence

`func (o *ContextSnapshotResponse) GetConfidence() string`

GetConfidence returns the Confidence field if non-nil, zero value otherwise.

### GetConfidenceOk

`func (o *ContextSnapshotResponse) GetConfidenceOk() (*string, bool)`

GetConfidenceOk returns a tuple with the Confidence field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConfidence

`func (o *ContextSnapshotResponse) SetConfidence(v string)`

SetConfidence sets Confidence field to given value.


### GetSignalsUsed

`func (o *ContextSnapshotResponse) GetSignalsUsed() int32`

GetSignalsUsed returns the SignalsUsed field if non-nil, zero value otherwise.

### GetSignalsUsedOk

`func (o *ContextSnapshotResponse) GetSignalsUsedOk() (*int32, bool)`

GetSignalsUsedOk returns a tuple with the SignalsUsed field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSignalsUsed

`func (o *ContextSnapshotResponse) SetSignalsUsed(v int32)`

SetSignalsUsed sets SignalsUsed field to given value.


### GetSummary

`func (o *ContextSnapshotResponse) GetSummary() string`

GetSummary returns the Summary field if non-nil, zero value otherwise.

### GetSummaryOk

`func (o *ContextSnapshotResponse) GetSummaryOk() (*string, bool)`

GetSummaryOk returns a tuple with the Summary field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSummary

`func (o *ContextSnapshotResponse) SetSummary(v string)`

SetSummary sets Summary field to given value.


### GetTopSignals

`func (o *ContextSnapshotResponse) GetTopSignals() []ContextSignalModel`

GetTopSignals returns the TopSignals field if non-nil, zero value otherwise.

### GetTopSignalsOk

`func (o *ContextSnapshotResponse) GetTopSignalsOk() (*[]ContextSignalModel, bool)`

GetTopSignalsOk returns a tuple with the TopSignals field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTopSignals

`func (o *ContextSnapshotResponse) SetTopSignals(v []ContextSignalModel)`

SetTopSignals sets TopSignals field to given value.

### HasTopSignals

`func (o *ContextSnapshotResponse) HasTopSignals() bool`

HasTopSignals returns a boolean if a field has been set.

### GetProjectsRanked

`func (o *ContextSnapshotResponse) GetProjectsRanked() []ProjectScoreModel`

GetProjectsRanked returns the ProjectsRanked field if non-nil, zero value otherwise.

### GetProjectsRankedOk

`func (o *ContextSnapshotResponse) GetProjectsRankedOk() (*[]ProjectScoreModel, bool)`

GetProjectsRankedOk returns a tuple with the ProjectsRanked field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProjectsRanked

`func (o *ContextSnapshotResponse) SetProjectsRanked(v []ProjectScoreModel)`

SetProjectsRanked sets ProjectsRanked field to given value.

### HasProjectsRanked

`func (o *ContextSnapshotResponse) HasProjectsRanked() bool`

HasProjectsRanked returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


