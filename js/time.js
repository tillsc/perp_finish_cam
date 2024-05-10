function _zpad(value, digits = 2) {
    return value.toString().padStart(digits, '0')
}

export function addSeconds(date, seconds) {
    if (date) {
      return new Date(date.getTime() + 1000 * seconds);
    }
}

export function formatTime(date) {
    if (date) {
        return `${_zpad(date.getHours())}:${_zpad(date.getMinutes())}:${_zpad(date.getSeconds())}.${_zpad(Math.floor(date.getMilliseconds() / 10))}`
    }
}