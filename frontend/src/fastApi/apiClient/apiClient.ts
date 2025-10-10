import { Configuration } from '@/fastApi/configuration'
import { DefaultApiAxiosParamCreator } from '@/fastApi/api'
import axios from "axios";

let accessToken = 'test'

export const configuration = new Configuration({
  basePath: '',
  accessToken,
})

export const creator = DefaultApiAxiosParamCreator(configuration)


export const request = async (requestArgsPromise: Promise<{
  url: string
  options: any
}>) => {
  const { url, options } = await requestArgsPromise
  const response = await axios.request({
    ...options,
    url,
    baseURL: configuration.basePath,
  })
  return response.data
}