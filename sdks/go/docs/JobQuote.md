# JobQuote

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**JobId** | **string** |  | 
**EstimatedCostCredits** | **float32** |  | 
**EstimatedTimeMs** | **int32** |  | 

## Methods

### NewJobQuote

`func NewJobQuote(jobId string, estimatedCostCredits float32, estimatedTimeMs int32, ) *JobQuote`

NewJobQuote instantiates a new JobQuote object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewJobQuoteWithDefaults

`func NewJobQuoteWithDefaults() *JobQuote`

NewJobQuoteWithDefaults instantiates a new JobQuote object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetJobId

`func (o *JobQuote) GetJobId() string`

GetJobId returns the JobId field if non-nil, zero value otherwise.

### GetJobIdOk

`func (o *JobQuote) GetJobIdOk() (*string, bool)`

GetJobIdOk returns a tuple with the JobId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetJobId

`func (o *JobQuote) SetJobId(v string)`

SetJobId sets JobId field to given value.


### GetEstimatedCostCredits

`func (o *JobQuote) GetEstimatedCostCredits() float32`

GetEstimatedCostCredits returns the EstimatedCostCredits field if non-nil, zero value otherwise.

### GetEstimatedCostCreditsOk

`func (o *JobQuote) GetEstimatedCostCreditsOk() (*float32, bool)`

GetEstimatedCostCreditsOk returns a tuple with the EstimatedCostCredits field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEstimatedCostCredits

`func (o *JobQuote) SetEstimatedCostCredits(v float32)`

SetEstimatedCostCredits sets EstimatedCostCredits field to given value.


### GetEstimatedTimeMs

`func (o *JobQuote) GetEstimatedTimeMs() int32`

GetEstimatedTimeMs returns the EstimatedTimeMs field if non-nil, zero value otherwise.

### GetEstimatedTimeMsOk

`func (o *JobQuote) GetEstimatedTimeMsOk() (*int32, bool)`

GetEstimatedTimeMsOk returns a tuple with the EstimatedTimeMs field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEstimatedTimeMs

`func (o *JobQuote) SetEstimatedTimeMs(v int32)`

SetEstimatedTimeMs sets EstimatedTimeMs field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


