import { IsString, MaxLength, MinLength } from 'class-validator';

export class AnalyzeRippleBrainDto {
  @IsString()
  @MinLength(10, { message: 'Change request must be at least 10 characters' })
  @MaxLength(4000, { message: 'Change request must be less than 4000 characters' })
  changeRequest: string;
}
