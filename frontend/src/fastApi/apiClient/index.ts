import {creator, request} from './apiClient'

export const indexApi = {
    getSubscription(payload: string) {
        return request(creator.getSubscription(payload))
    },

    confirmWithoutSupport(payload: string) {
        return request(creator.confirmWithoutSupport(payload))
    },

    getSocialMedia() {
        return request(creator.getSocialMedia())
    },
}