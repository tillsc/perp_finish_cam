export function addSeconds(date, seconds) {
    if (date) {
      return new Date(date.getTime() + 1000 * seconds);
    }
}

/**
 * Subtracts two given Dates only looking at the times
 * ignoring their date components.
 * @param {Date} date1
 * @param {Date} date2
 * @returns {number} Number of milliseconds between time components of given dates
 */
export function timeDifferenceInMilliseconds(date1, date2) {
    if (!date1 || !date2) {
        return;
    }
    else if (date1.getTimezoneOffset() !== date2.getTimezoneOffset()) {
        console.log("Warning: Subtracting times based on to Dates with different timezones may lead to unexpected problems!", date1, date2)
    }

    return (date1.getTime() % 86_400_000) - (date2.getTime() % 86_400_000);
}

/**
 * Subtracts two given Dates only looking at the times
 * ignoring their date components.
 * @param {Date} date1
 * @param {Date} date2
 * @returns {Date} A date based on the date component of date1 holding a time component representing the time difference of date1 and date2
 */
export function timeDifference(date1, date2) {
    if (!date1 || !date2) {
        return;
    }

    const ts = timeDifferenceInMilliseconds(date1, date2) +
      date1.getTime() - (date1.getTime() % 86_400_000) +
      (date1.getTimezoneOffset() * 60_000)

    return new Date(ts);
}

export function formatTime(date, optionalHours) {
    if (date) {
        let hoursAndMinutes;
        if ( date.getHours() === 0 && optionalHours) {
            hoursAndMinutes = date.getMinutes().toString();
        }
        else {
            hoursAndMinutes = `${_zpad(date.getHours())}:${_zpad(date.getMinutes())}`;
        }
        return `${hoursAndMinutes}:${_zpad(date.getSeconds())}.${_zpad(Math.floor(date.getMilliseconds() / 10))}`
    }
}

export function parseTime2(timeString, baseDate) {
    baseDate = baseDate || new Date();
    return new Date(`${baseDate.toDateString()} ${timeString}`)
}

export function parseTime(timeString, baseDate = new Date()) {
    const [h = "0", m = "0", s = "0"] = timeString.split(":");
    const [sh, sm] = s.split(".");
    const ms = sm ? parseInt((sm + "00").slice(0, 3)) : 0;

    const date = new Date(baseDate);
    date.setHours(+h);
    date.setMinutes(+m);
    date.setSeconds(+sh || 0);
    date.setMilliseconds(ms);
    return date;
}

function _zpad(value, digits = 2) {
    return value.toString().padStart(digits, '0')
}
