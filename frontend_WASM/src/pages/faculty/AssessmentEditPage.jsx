import React from 'react';
import CreateAssessmentWizard from './CreateAssessmentWizard';
import { useParams } from 'react-router-dom';

const AssessmentEditPage = () => {
  const { id } = useParams();
  return <CreateAssessmentWizard isEdit={true} assessmentId={id} />;
};

export default AssessmentEditPage;
