namespace Babylon60.Kernel

open System

module FixedPoint =
    // Scale factor: 60^3 = 216000
    [<Literal>]
    let Scale = 216000L

    [<Struct>]
    type Fixed60 = 
        { RawValue: int64 }
        
        static member Create(integerPart: int64) =
            { RawValue = integerPart * Scale }
            
        static member Create(deg: int64, min: int64, sec: int64, third: int64) =
            let sign = if deg < 0L || min < 0L || sec < 0L || third < 0L then -1L else 1L
            let absDeg = abs deg
            let absMin = abs min
            let absSec = abs sec
            let absThird = abs third
            let total = absDeg * Scale + absMin * 3600L + absSec * 60L + absThird
            { RawValue = sign * total }

        static member ToDegMinSecThird(f: Fixed60) =
            let sign = if f.RawValue < 0L then -1L else 1L
            let absVal = abs f.RawValue
            let deg = absVal / Scale
            let rem1 = absVal % Scale
            let min = rem1 / 3600L
            let rem2 = rem1 % 3600L
            let sec = rem2 / 60L
            let third = rem2 % 60L
            (sign * deg, min, sec, third)

        static member Add(a: Fixed60, b: Fixed60) =
            { RawValue = a.RawValue + b.RawValue }

        static member Sub(a: Fixed60, b: Fixed60) =
            { RawValue = a.RawValue - b.RawValue }

        static member Mul(a: Fixed60, b: Fixed60) =
            let bigA = bigint a.RawValue
            let bigB = bigint b.RawValue
            let bigS = bigint Scale
            let res = (bigA * bigB) / bigS
            { RawValue = int64 res }

        static member Div(a: Fixed60, b: Fixed60) =
            let bigA = bigint a.RawValue
            let bigB = bigint b.RawValue
            let bigS = bigint Scale
            let res = (bigA * bigS) / bigB
            { RawValue = int64 res }

        member this.ToFloat() =
            double this.RawValue / double Scale

        static member FromFloat(x: double) =
            { RawValue = int64 (round (x * double Scale)) }

        override this.ToString() =
            let (d, m, s, t) = Fixed60.ToDegMinSecThird(this)
            sprintf "%d°%02d'%02d\"%02d'''" d m s t
