# JobSLA

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ConfidenceLevel** | **string** |  | 
**MaxLatencyMs** | **int32** |  | 
**RequiresZkProof** | **bool** |  | 

## Methods

### NewJobSLA

`func NewJobSLA(confidenceLevel string, maxLatencyMs int32, requiresZkProof bool, ) *JobSLA`

NewJobSLA instantiates a new JobSLA object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewJobSLAWithDefaults

`func NewJobSLAWithDefaults() *JobSLA`

NewJobSLAWithDefaults instantiates a new JobSLA object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetConfidenceLevel

`func (o *JobSLA) GetConfidenceLevel() string`

GetConfidenceLevel returns the ConfidenceLevel field if non-nil, zero value otherwise.

### GetConfidenceLevelOk

`func (o *JobSLA) GetConfidenceLevelOk() (*string, bool)`

GetConfidenceLevelOk returns a tuple with the ConfidenceLevel field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConfidenceLevel

`func (o *JobSLA) SetConfidenceLevel(v string)`

SetConfidenceLevel sets ConfidenceLevel field to given value.


### GetMaxLatencyMs

`func (o *JobSLA) GetMaxLatencyMs() int32`

GetMaxLatencyMs returns the MaxLatencyMs field if non-nil, zero value otherwise.

### GetMaxLatencyMsOk

`func (o *JobSLA) GetMaxLatencyMsOk() (*int32, bool)`

GetMaxLatencyMsOk returns a tuple with the MaxLatencyMs field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMaxLatencyMs

`func (o *JobSLA) SetMaxLatencyMs(v int32)`

SetMaxLatencyMs sets MaxLatencyMs field to given value.


### GetRequiresZkProof

`func (o *JobSLA) GetRequiresZkProof() bool`

GetRequiresZkProof returns the RequiresZkProof field if non-nil, zero value otherwise.

### GetRequiresZkProofOk

`func (o *JobSLA) GetRequiresZkProofOk() (*bool, bool)`

GetRequiresZkProofOk returns a tuple with the RequiresZkProof field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRequiresZkProof

`func (o *JobSLA) SetRequiresZkProof(v bool)`

SetRequiresZkProof sets RequiresZkProof field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


