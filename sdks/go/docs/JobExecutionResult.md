# JobExecutionResult

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**JobId** | **string** |  | 
**Status** | **string** |  | 
**Result** | **map[string]interface{}** | Graph-RAG context (subgraph or related entities) | 
**Proof** | **NullableString** |  | 
**ExecutedAt** | **string** |  | 

## Methods

### NewJobExecutionResult

`func NewJobExecutionResult(jobId string, status string, result map[string]interface{}, proof NullableString, executedAt string, ) *JobExecutionResult`

NewJobExecutionResult instantiates a new JobExecutionResult object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewJobExecutionResultWithDefaults

`func NewJobExecutionResultWithDefaults() *JobExecutionResult`

NewJobExecutionResultWithDefaults instantiates a new JobExecutionResult object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetJobId

`func (o *JobExecutionResult) GetJobId() string`

GetJobId returns the JobId field if non-nil, zero value otherwise.

### GetJobIdOk

`func (o *JobExecutionResult) GetJobIdOk() (*string, bool)`

GetJobIdOk returns a tuple with the JobId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetJobId

`func (o *JobExecutionResult) SetJobId(v string)`

SetJobId sets JobId field to given value.


### GetStatus

`func (o *JobExecutionResult) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *JobExecutionResult) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *JobExecutionResult) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetResult

`func (o *JobExecutionResult) GetResult() map[string]interface{}`

GetResult returns the Result field if non-nil, zero value otherwise.

### GetResultOk

`func (o *JobExecutionResult) GetResultOk() (*map[string]interface{}, bool)`

GetResultOk returns a tuple with the Result field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetResult

`func (o *JobExecutionResult) SetResult(v map[string]interface{})`

SetResult sets Result field to given value.


### SetResultNil

`func (o *JobExecutionResult) SetResultNil(b bool)`

 SetResultNil sets the value for Result to be an explicit nil

### UnsetResult
`func (o *JobExecutionResult) UnsetResult()`

UnsetResult ensures that no value is present for Result, not even an explicit nil
### GetProof

`func (o *JobExecutionResult) GetProof() string`

GetProof returns the Proof field if non-nil, zero value otherwise.

### GetProofOk

`func (o *JobExecutionResult) GetProofOk() (*string, bool)`

GetProofOk returns a tuple with the Proof field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProof

`func (o *JobExecutionResult) SetProof(v string)`

SetProof sets Proof field to given value.


### SetProofNil

`func (o *JobExecutionResult) SetProofNil(b bool)`

 SetProofNil sets the value for Proof to be an explicit nil

### UnsetProof
`func (o *JobExecutionResult) UnsetProof()`

UnsetProof ensures that no value is present for Proof, not even an explicit nil
### GetExecutedAt

`func (o *JobExecutionResult) GetExecutedAt() string`

GetExecutedAt returns the ExecutedAt field if non-nil, zero value otherwise.

### GetExecutedAtOk

`func (o *JobExecutionResult) GetExecutedAtOk() (*string, bool)`

GetExecutedAtOk returns a tuple with the ExecutedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExecutedAt

`func (o *JobExecutionResult) SetExecutedAt(v string)`

SetExecutedAt sets ExecutedAt field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


